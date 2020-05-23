"""A poker engine"""
from enum import Enum, auto
from collections import namedtuple
from random import shuffle


class EventRejected(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)


class PlayerState:
    WAITING_NEW_GAME = "WAITING_NEW_GAME"
    MY_TURN = "MY_TURN"
    IN_GAME = "IN_GAME"
    FOLDED = "FOLDED"

    @classmethod
    def could_play(cls, state):
        return (
                state == cls.MY_TURN
                or state == cls.IN_GAME
        )

    @classmethod
    def is_in_game(cls, state):
        return (
                state == cls.MY_TURN
                or state == cls.IN_GAME
                or state == cls.FOLDED
        )


class GameState:
    NOT_STARTED = "NOT_STARTED"
    PREFLOP = "PREFLOP"
    FLOP = "FLOP"
    RIVER = "RIVER"
    TURN = "TURN"
    GAME_OVER = "GAME_OVER"

    @classmethod
    def is_ongoing(cls, state):
        return state == cls.PREFLOP or state == cls.RIVER or state == cls.FLOP or state == cls.TURN


class Suit:
    SPADE = "SPADE"
    DIAMONDS = "DIAMONDS"
    HEART = "HEART"
    CLUBS = "CLUBS"


class MessageType:
    GAME_OVER = "GAME_OVER"
    DRINK = "DRINK"


Card = namedtuple("Card", "value suit")

card_values = range(2, 15)  # J = 11, Q = 12, K = 13, As = 14 for sorting reasons

deck = (
        tuple([(Card(value=x, suit=Suit.SPADE)) for x in card_values])
        + tuple([(Card(value=x, suit=Suit.DIAMONDS)) for x in card_values])
        + tuple([(Card(value=x, suit=Suit.HEART)) for x in card_values])
        + tuple([(Card(value=x, suit=Suit.CLUBS)) for x in card_values])
)


def shuffle_deck():
    the_deck = list(deck)
    shuffle(the_deck)
    return the_deck


def initial_state():
    """
    The initial state, any state should *always* be serializable to json
    Players is a dict with who's playing order as keys
    """
    return {
        'deck': shuffle_deck(),
        'flop': [],
        'seats': {
            "1": "",
            "2": "",
            "3": "",
            "4": "",
            "5": "",
            "6": "",
            "7": "",
            "8": "",
            "9": "",
            "10": ""
        },
        'turn_to': -1,
        'players': {},
        'game_state': GameState.NOT_STARTED,
        'dealing': '',
        'small_blind': 2,
        'big_blind': 2
    }


class EventProcessingFailed(Exception):

    def __init__(self, explanation):
        self.explanation = explanation


class Event(Enum):
    PLAYER_SIT = auto()
    PLAYER_LEAVE = auto()
    PLAYER_READY_FOR_NEXT_GAME = auto()
    START_GAME = auto()
    FOLD = auto()
    CHECK = auto()
    CALL = auto()
    NONE = auto()
    DRAW_FLOP = auto()
    DRAW_RIVER = auto()
    DRAW_TURN = auto()

    @staticmethod
    def make_event(event):
        return {"type": event} if Event is not None else None


def rotate(l, n):
    return l[n:] + l[:n]


def is_table_empty(state):
    return not bool(state["players"])


def strip_state_for_player(state, player_id):
    if "deck" in state:
        del state["deck"]
    for a_player_id in state["players"]:
        if player_id != a_player_id:
            if "cards" in state["players"][a_player_id]:
                del state["players"][a_player_id]["cards"]
    return state


def determine_next(state, current):
    seats_in_order = sorted([
        seat_number
        for seat_number in state["seats"]
    ], key=lambda x: int(x))
    for seat_number in rotate(seats_in_order, int(current)):
        if state["seats"][seat_number]:
            return seat_number
    raise EventRejected("Trying to determine next on an empty table")


def determine_next_dealer_seat(state):
    current_dealer_seat = state["dealing"] if state["dealing"] else "1"
    return determine_next(state, current_dealer_seat)


def validate_check_or_call_or_fold(state, player_id):
    if not GameState.is_ongoing(state["game_state"]):
        raise EventRejected("Player check when game is not ongoing")
    if player_id not in state["players"]:
        raise EventRejected(f"Player {player_id} is unknown")
    if state["players"][player_id]["state"] != PlayerState.MY_TURN:
        raise EventRejected(f"Player {player_id} is trying to check on not their turn")


def start_game(state):
    if len(state["players"]) < 2:
        return None, state

    for player_id in state["players"]:
        state["players"][player_id]["state"] = PlayerState.IN_GAME
        state["players"][player_id]["committed_by"] = 0

    state["flop"] = []

    state["dealing"] = determine_next_dealer_seat(state)
    state["deck"] = shuffle_deck()
    sitted_players_ids = [
        player_id
        for (seat_number, player_id) in sorted(state["seats"].items(), key=lambda x: int(x[0]))
        if player_id
    ]
    sitted_players_ids_starting_after_dealer = rotate(
        sitted_players_ids,
        sitted_players_ids.index(
            state["seats"][state["dealing"]]
        ) + 1
    )
    # Deal 2 cards to all players, without respecting the poker rules
    # because it's random anyway
    for player_id in sitted_players_ids:
        state["players"][player_id]["cards"] = [state["deck"].pop(0), state["deck"].pop(0)]
    state["game_state"] = GameState.PREFLOP
    # Blinds and set who's turn it is to play
    state["players"][
        sitted_players_ids_starting_after_dealer[-1]
    ]["state"] = PlayerState.MY_TURN
    state["players"][
        sitted_players_ids_starting_after_dealer[-3 % len(sitted_players_ids_starting_after_dealer)]
    ]["committed_by"] = state["small_blind"]
    state["players"][
        sitted_players_ids_starting_after_dealer[-2]
    ]["committed_by"] = state["big_blind"]

    return None, state


def sit_player(state, player_id, player_name, seat_number):
    if state["seats"][str(seat_number)]:
        raise EventRejected("A player already sits there")
    if player_id in state["players"]:
        raise EventRejected("Player with that id is already seated")

    state["players"][player_id] = {
        "name": player_name,
        "state": PlayerState.WAITING_NEW_GAME
    }
    state["seats"][str(seat_number)] = player_id

    if sum([1 if seated_player_id else 0 for seated_player_id in state["seats"].values()]) > 1 \
            and state["game_state"] == GameState.NOT_STARTED:
        event = {"type": Event.START_GAME}
    else:
        event = None

    return event, state


def exclude_player(state, the_player_id):
    if the_player_id not in state["players"]:
        raise EventRejected("Excluding a player who's not here")
    if (
            count_if(state["players"].values(), lambda player: PlayerState.is_in_game(player["state"])) <= 2
            and PlayerState.is_in_game(state["players"][the_player_id]["state"])
    ):
        # Only one playing player left that's not waiting for new game, game ends
        state["dealing"] = ""
        state["game_state"] = GameState.NOT_STARTED
        state["flop"] = []
        for player_id in state["players"]:
            state["players"][player_id] = {
                "state": PlayerState.WAITING_NEW_GAME,
                "name": state["players"][player_id]["name"]
            }
    elif state["players"][the_player_id]["state"] == PlayerState.MY_TURN:
        # The player who left was in hand
        (players_after_current_not_folded,
         players_before_current_not_folded_not_aligned) = determine_next_players_for_this_round(state, the_player_id)
        next_player_id = (players_after_current_not_folded + players_before_current_not_folded_not_aligned)[0]
        state["players"][next_player_id]["state"] = PlayerState.MY_TURN

    # Remove player from seats
    state["seats"] = {
        seat_number: player_id if player_id != the_player_id else ""
        for seat_number, player_id in state["seats"].items()
    }
    # Remove player
    del state["players"][the_player_id]

    event = None
    if len(state["players"]) >= 2 and state["game_state"] == GameState.NOT_STARTED:
        event = {
            "type": Event.START_GAME
        }
    elif all_folded_but_one(state["players"]):
        # Game is over
        state["game_state"] = GameState.GAME_OVER
        state["results"] = generate_end_game_results(state)

    return event, state


def list_of_players_ids_starting_at_dealer(seats, dealer):
    player_ids_in_order = [
        seat_player_tuple[1]
        for seat_player_tuple in sorted(
            seats.items(),
            key=lambda seat_player_tuple: int(seat_player_tuple[0])
        )
    ]
    return rotate(player_ids_in_order, int(dealer) - 1)


def remove_empty(a_string_list):
    return [x for x in a_string_list if x]


def count_if(list_, predicate):
    return sum([1 for x in list_ if predicate(x)])


def find_player_ids_if(players, predicate):
    return [x[0] for x in players.items() if predicate(x[1])]


def all_folded_but_one(players):
    folded_count = count_if(players.values(), lambda player: player["state"] == PlayerState.FOLDED)
    in_game_count = count_if(players.values(), lambda player: PlayerState.is_in_game(player["state"]))
    return in_game_count - folded_count == 1


def get_max_bet(state):
    return max([
        player["committed_by"]
        for player in state["players"].values()
        if "committed_by" in player
    ])


def next_state_event(game_state):

    def event_type():
        if game_state == GameState.PREFLOP:
            return Event.DRAW_FLOP
        elif game_state == GameState.FLOP:
            return Event.DRAW_RIVER
        elif game_state == GameState.RIVER:
            return Event.DRAW_TURN
        else:
            print(f"No event for game state: {game_state}")
            return None

    return Event.make_event(event_type())


def determine_next_players_for_this_round(state, current_player_id):
    """
    Returns a tuple: (
        [1]: players after current player that are not folded
        [2]: players before current player that are not folder AND not aligned with the max bet
    )
    """
    players_in_order = remove_empty(
        list_of_players_ids_starting_at_dealer(
            state["seats"],
            state["dealing"] if state["dealing"] else "1"
        )
    )

    # Find out players that have to play in order:
    current_player_index = players_in_order.index(current_player_id)
    # players after the current player that are not folded
    players_after_current_not_folded = [
        player_id
        for player_id in players_in_order[current_player_index + 1:]
        if state["players"][player_id]["state"] == PlayerState.IN_GAME
    ]
    # players before the current player that are not folded AND not aligned with the max bet
    players_before_current = players_in_order[:current_player_index]
    max_bet = get_max_bet(state)
    players_before_current_not_folded_not_aligned = [
        player_id_
        for player_id_ in players_before_current
        if (state["players"][player_id_]["state"] == PlayerState.IN_GAME
            and state["players"][player_id_]["committed_by"] < max_bet)
    ]

    return players_after_current_not_folded, players_before_current_not_folded_not_aligned


def generate_end_game_results(state):
    return {
        "winner": find_player_ids_if(
            state["players"],
            lambda player: PlayerState.is_in_game(player["state"]) and player["state"] != PlayerState.FOLDED
        )[0],
        "drinkers": {
            player_id: state["players"][player_id]["committed_by"]
            for player_id in find_player_ids_if(
                state["players"],
                lambda player: player["state"] == PlayerState.FOLDED
            )
            if "committed_by" in state["players"][player_id]
        }
    }


def fold_player(state, player_id):

    validate_check_or_call_or_fold(state, player_id)

    (players_after_current_not_folded,
     players_before_current_not_folded_not_aligned) = determine_next_players_for_this_round(state, player_id)

    state["players"][player_id]["state"] = PlayerState.FOLDED
    event = None
    if players_after_current_not_folded and not all_folded_but_one(state["players"]):
        state["players"][players_after_current_not_folded[0]]["state"] = PlayerState.MY_TURN
    elif players_before_current_not_folded_not_aligned:
        state["players"][players_before_current_not_folded_not_aligned[0]]["state"] = PlayerState.MY_TURN
    else:
        # Either game ends if we're at the turn or all folded but one
        if (state["game_state"] == GameState.TURN
                or all_folded_but_one(state["players"])):
            state["results"] = generate_end_game_results(state)
            state["game_state"] = GameState.GAME_OVER
        # Or draw next state
        else:
            event = next_state_event(state["game_state"])

    return event, state


def player_ready(state, player_id):
    if state["game_state"] != GameState.GAME_OVER:
        return None, state

    state["players"][player_id]["state"] = PlayerState.WAITING_NEW_GAME

    all_ready = count_if(
        state["players"].values(),
        lambda player: player["state"] == PlayerState.WAITING_NEW_GAME
    ) == len(state["players"])

    return (
        Event.make_event(Event.START_GAME) if all_ready else None,
        state
    )


def player_check(state, player_id):

    validate_check_or_call_or_fold(state, player_id)

    current_player = state["players"][player_id]
    if current_player["committed_by"] < get_max_bet(state):
        raise EventRejected(f"Player {player_id} is trying to check when should call or raise")

    players_after_current_not_folded, _ = determine_next_players_for_this_round(state, player_id)

    state["players"][player_id]["state"] = PlayerState.IN_GAME
    event = None
    if players_after_current_not_folded:
        state["players"][players_after_current_not_folded[0]]["state"] = PlayerState.MY_TURN
    else:
        event = next_state_event(state["game_state"])

    return event, state


def draw_flop(state):
    if "deck" not in state or not state["deck"] or len(state["deck"]) < 3:
        raise EventRejected("Not deck, can't draw flop")

    if "dealing" not in state or state["dealing"] == "":
        state["dealing"] = "1"

    in_game_players_starting_at_dealer = list(filter(
        lambda player_id: PlayerState.could_play(state["players"][player_id]["state"]),
        remove_empty(list_of_players_ids_starting_at_dealer(state["seats"], state["dealing"]))
    ))

    if not in_game_players_starting_at_dealer:
        raise EventRejected("Something went very wrong, no next player on draw event")

    next_player_id = in_game_players_starting_at_dealer[0]
    state["players"][next_player_id]["state"] = PlayerState.MY_TURN
    state["game_state"] = GameState.FLOP
    state["flop"] = [state["deck"].pop(0), state["deck"].pop(0), state["deck"].pop(0)]

    return None, state


def player_call(state, player_id):

    validate_check_or_call_or_fold(state, player_id)

    current_player = state["players"][player_id]
    max_bet = get_max_bet(state)
    if current_player["committed_by"] < max_bet:
        current_player["committed_by"] = max_bet

    (players_after_current_not_folded,
     players_before_current_not_folded_not_aligned) = determine_next_players_for_this_round(state, player_id)

    state["players"][player_id]["state"] = PlayerState.IN_GAME
    event = None
    if players_after_current_not_folded:
        state["players"][players_after_current_not_folded[0]]["state"] = PlayerState.MY_TURN
    elif players_before_current_not_folded_not_aligned:
        state["players"][players_before_current_not_folded_not_aligned[0]]["state"] = PlayerState.MY_TURN
    else:
        event = next_state_event(state["game_state"])

    return event, state


def process_event(state, event):

    if event["type"] == Event.PLAYER_SIT:
        event, new_state = sit_player(
            state,
            event["player_id"],
            event["parameters"]["player_name"],
            event["parameters"]["seat_number"]
        )
    elif event["type"] == Event.PLAYER_LEAVE:
        event, new_state = exclude_player(
            state,
            event["player_id"]
        )
    elif event["type"] == Event.START_GAME:
        event, new_state = start_game(state)
    elif event["type"] == Event.FOLD:
        event, new_state = fold_player(
            state,
            event["player_id"]
        )
    elif event["type"] == Event.PLAYER_READY_FOR_NEXT_GAME:
        event, new_state = player_ready(
            state,
            event["player_id"]
        )
    elif event["type"] == Event.CHECK:
        event, new_state = player_check(
            state,
            event["player_id"]
        )
    elif event["type"] == Event.DRAW_FLOP:
        event, new_state = draw_flop(state)
    elif event["type"] == Event.CALL:
        event, new_state = player_call(
            state,
            event["player_id"]
        )
    else:
        print(f"WARNING: unknown event type: {event['type']}")
        event, new_state = None, state

    if event:
        return process_event(new_state, event)
    else:
        return new_state
