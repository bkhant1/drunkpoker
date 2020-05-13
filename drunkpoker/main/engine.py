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


class Suit:
    SPADE = "SPADE"
    DIAMONDS = "DIAMONDS"
    HEART = "HEART"
    CLUBS = "CLUBS"


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
        'small_blind': 1,
        'big_blind': 2
    }


class EventProcessingFailed(Exception):

    def __init__(self, explanation):
        self.explanation = explanation


class Event(Enum):
    PLAYER_SIT = auto()
    PLAYER_LEAVE = auto()
    START_GAME = auto()
    NONE = auto()


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


def determine_next_player(state):
    current_player = next(filter(
        lambda x: state["players"][x]["state"] == PlayerState.MY_TURN,
        state["players"]
    ))
    current_player_seat = [
        seat for seat, player_id in state["seats"].items()
        if player_id == current_player
    ][0]
    return state["seats"][determine_next(state, current_player_seat)]


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
        sitted_players_ids_starting_after_dealer[0]
    ]["state"] = PlayerState.MY_TURN
    state["players"][
        sitted_players_ids_starting_after_dealer[-2]
    ]["committed_by"] = state["small_blind"]
    state["players"][
        sitted_players_ids_starting_after_dealer[-1]
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
        sum([1 for player in state["players"].values() if PlayerState.is_in_game(player["state"])]) <= 2
        and PlayerState.is_in_game(state["players"][the_player_id]["state"])
    ):
        # Only one playing player left, game ends
        state["dealing"] = ""
        state["game_state"] = GameState.NOT_STARTED
        for player_id in state["players"]:
            state["players"][player_id] = {
                "state": PlayerState.WAITING_NEW_GAME,
                "name": state["players"][player_id]["name"]
            }
    elif state["players"][the_player_id]["state"] == PlayerState.MY_TURN:
        # The player who left was in hand
        next_player_id = determine_next_player(state)
        state["players"][next_player_id]["state"] = PlayerState.MY_TURN

    # Remove player from seats
    state["seats"] = {
        seat_number: player_id if player_id != the_player_id else ""
        for seat_number, player_id in state["seats"].items()
    }
    # Remove player
    del state["players"][the_player_id]

    if len(state["players"]) >= 2 and state["game_state"] == GameState.NOT_STARTED:
        event = {
            "type": Event.START_GAME
        }
    else:
        event = None
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

    if event:
        return process_event(new_state, event)
    else:
        return new_state
