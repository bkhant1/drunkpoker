"""A poker engine"""
from enum import Enum, auto
from collections import namedtuple
from random import shuffle
from itertools import groupby
from typing import List, Tuple
import copy


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

    @classmethod
    def enumerate_state(cls):
        return [
            cls.__dict__[it] for it in cls.__dict__
            if isinstance(cls.__dict__[it], str) and '__' not in it
        ]


class Suit:
    SPADE = "SPADE"
    DIAMONDS = "DIAMONDS"
    HEART = "HEART"
    CLUBS = "CLUBS"


class MessageType:
    GAME_OVER = "GAME_OVER"
    DRINK = "DRINK"


class Combinations:
    HIGH_CARD = 0
    ONE_PAIR = 1
    TWO_PAIRS = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8


"""
Probably don't want to change that as the python natural tuple comparison is used. Combination is a number and 
best_cards a tuple of numbers
"""
Result = namedtuple("Result", "combination best_cards")

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


def initial_state(game_type="drinking"):
    """
    The initial state, any state should *always* be serializable to json
    Players is a dict with who's playing order as keys
    """
    return {
        'deck': shuffle_deck(),
        'community_cards': [],
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
        'small_blind': 1 if game_type == "drinking" else 10,
        'big_blind': 2 if game_type == "drinking" else 20,
        'all_in': 20,  # Maximum sips all-in, unused for normal game
        'game_type': game_type,
        'players_stacks': {}  # Memory of the size of a player stack, unused for drinking game
    }


class EventProcessingFailed(Exception):

    def __init__(self, explanation):
        self.explanation = explanation


class Event(Enum):
    PLAYER_SIT = auto()
    PLAYER_LEAVE = auto()
    PLAYER_READY_FOR_NEXT_GAME = auto()
    PLAYERS_LOST = auto()
    START_GAME = auto()
    FOLD = auto()
    CHECK = auto()
    CALL = auto()
    RAISE = auto()
    END_GAME = auto()
    RESOLVE_STACKS = auto()
    SHOW_CARDS = auto()
    NONE = auto()
    DRAW_FLOP = auto()
    DRAW_RIVER = auto()
    DRAW_TURN = auto()
    MULTI_EVENT = auto()

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
    game_over = state["game_state"] == GameState.GAME_OVER
    should_show_cards_because_end_of_game = (
            not all_folded_but_one(state["players"])
            and game_over
    )

    def player_shows_cards(player_id_):
        return ("show_cards" in state["players"][a_player_id]
                and state["players"][a_player_id]["show_cards"])

    for a_player_id in state["players"]:
        if player_id != a_player_id:
            should_show_cards_anyway = (
                    (should_show_cards_because_end_of_game
                     and (PlayerState.could_play(state["players"][a_player_id]["state"])
                          or player_shows_cards(a_player_id)))
                    or game_over and player_shows_cards(a_player_id)
            )

            if "cards" in state["players"][a_player_id] and not should_show_cards_anyway:
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
        raise EventRejected("Player check or call or fold when game is not ongoing")
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
        if "show_cards" in state["players"][player_id]:
            del state["players"][player_id]["show_cards"]

    state["community_cards"] = []

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
        "state": PlayerState.WAITING_NEW_GAME,
        "committed_by": 0
    }
    state["seats"][str(seat_number)] = player_id

    if state["game_type"] == "normal":
        if player_id not in state["players_stacks"]:
            state["players_stacks"][player_id] = 1000

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
        state["community_cards"] = []
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


def find_player_ids_if(players, predicate) -> List[str]:
    return [x[0] for x in players.items() if predicate(x[1])]


def all_folded_but_one(players):
    folded_count = count_if(players.values(), lambda player: player["state"] == PlayerState.FOLDED)
    in_game_count = count_if(players.values(), lambda player: PlayerState.is_in_game(player["state"]))
    return in_game_count - folded_count == 1


def all_players_all_in(state):
    if state["game_type"] != "normal":
        return all([
            (True if ("committed_by" in player and player["committed_by"] == state["all_in"])
                     or not PlayerState.could_play(player["state"])
             else False)
            for player in state["players"].values()
        ])
    else:
        players_in_game_not_folded_and_maxed_out = {
            player_id for player_id, player in state["players"].items()
            if (
                "committed_by" in state["players"][player_id]
                and state["players_stacks"][player_id] == player["committed_by"]
            )
        }
        players_in_game_and_not_folded = {
            player_id for player_id, player in state["players"].items()
            if PlayerState.could_play(player["state"])
        }
        players_in_game_not_maxed_out = players_in_game_and_not_folded - players_in_game_not_folded_and_maxed_out
        if len(players_in_game_not_maxed_out) > 1:
            return False
        elif len(players_in_game_not_maxed_out) == 0:
            return True
        else:
            return state["players"][players_in_game_not_maxed_out.pop()]["committed_by"] == get_max_bet(state)


def all_aligned(state):
    players = state["players"].values()
    one_player_in_game_commitment = [
        player["committed_by"] for player in players
        if PlayerState.could_play(player["state"])
    ][0]
    return all([
        player["committed_by"] == one_player_in_game_commitment
        for player in players
    ])


def get_max_bet(state):
    return max([
        player["committed_by"]
        for player in state["players"].values()
        if "committed_by" in player
    ] + [0])


def next_state_event(game_state):
    def event_type():
        if game_state == GameState.PREFLOP:
            return Event.DRAW_FLOP
        elif game_state == GameState.FLOP:
            return Event.DRAW_RIVER
        elif game_state == GameState.RIVER:
            return Event.DRAW_TURN
        elif game_state == GameState.TURN:
            return Event.END_GAME
        else:
            print(f"No event for game state: {game_state}")
            return None

    return Event.make_event(event_type())


def determine_next_players_for_this_round(state, current_player_id):
    """
    Returns a tuple: (
        [1]: players after current player that are not folded (AND not all-in for normal game)
        [2]: players before current player that are not folded AND not aligned with the max bet (AND not all-in
             for normal game)
    )
    """
    players_in_order = remove_empty(
        list_of_players_ids_starting_at_dealer(
            state["seats"],
            state["dealing"] if state["dealing"] else "1"
        )
    )

    def is_in_game(player_id):
        return (
            state["players"][player_id]["state"] == PlayerState.IN_GAME
            and (
                state["game_type"] != "normal"
                or int(state["players_stacks"][player_id]) > int(state["players"][player_id]["committed_by"])
            )
        )

    # Find out players that have to play in order:
    current_player_index = players_in_order.index(current_player_id)
    # players after the current player that are not folded
    players_after_current_not_folded = [
        player_id
        for player_id in players_in_order[current_player_index + 1:]
        if is_in_game(player_id)
    ]
    # players before the current player that are not folded AND not aligned with the max bet
    players_before_current = players_in_order[:current_player_index]
    max_bet = get_max_bet(state)
    players_before_current_not_folded_not_aligned = [
        player_id_
        for player_id_ in players_before_current
        if (is_in_game(player_id_)
            and (
                state["players"][player_id_]["committed_by"] if "committed_by" in state["players"][player_id_] else 0
            ) < max_bet)
    ]

    return players_after_current_not_folded, players_before_current_not_folded_not_aligned


def rank_players(players, community_cards) -> List[List[Tuple[str, Result]]]:
    def key(player_id_combination_tuple):
        return player_id_combination_tuple[1]

    return [
        list(players)
        for _, players in groupby(
            sorted(
                [
                    (player_id, best_combination(players[player_id]["cards"] + community_cards))
                    for player_id in players
                ],
                key=key,
                reverse=True
            ),
            key=key
        )
    ]


def generate_end_game_results(state):
    # By fold
    if all_folded_but_one(state["players"]):
        folded_players = find_player_ids_if(
            state["players"],
            lambda player: player["state"] == PlayerState.FOLDED
        )
        non_folded_player = find_player_ids_if(
            state["players"],
            lambda player: PlayerState.is_in_game(player["state"]) and player["state"] != PlayerState.FOLDED
        )
        return {
            "winners": non_folded_player,
            "drinkers": {
                player_id: state["players"][player_id]["committed_by"]
                for player_id in folded_players
                if "committed_by" in state["players"][player_id]
            },
            "scores": {
                player_id: None
                for player_id in find_player_ids_if(
                    state["players"],
                    lambda player: PlayerState.is_in_game(player["state"])
                )
            },
            "ranking": [non_folded_player] + [folded_players]
        }
    # By end of turn round
    else:
        # Looks like:
        # [
        #   [(P1, score), (P2, score)]
        #   [(P3, score)]
        #   ...
        # ]
        players_ranked_with_score = rank_players(
            {
                player_id: player
                for player_id, player in state["players"].items()
                if PlayerState.could_play(player["state"])
            },
            state["community_cards"]
        )
        winners_ids = [player_score[0] for player_score in players_ranked_with_score[0]]
        folded_player_ids = find_player_ids_if(state["players"], lambda player: player["state"] == PlayerState.FOLDED)
        losers_ids = folded_player_ids + [
            looser_and_score[0]
            for list_of_losers_scores in players_ranked_with_score[1:]
            for looser_and_score in list_of_losers_scores
        ]
        scores = {
            looser_and_score[0]: looser_and_score[1]
            for list_of_losers_scores in players_ranked_with_score
            for looser_and_score in list_of_losers_scores
        }
        return {
            "winners": winners_ids,
            "drinkers": {
                loser_id: state["players"][loser_id]["committed_by"]
                for loser_id in losers_ids
                if "committed_by" in state["players"][loser_id]
            },
            "scores": scores,
            "ranking": [
                [player_id_and_score[0] for player_id_and_score in list_of_players_and_score]
                for list_of_players_and_score in players_ranked_with_score
            ] + [folded_player_ids]
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
            event = Event.make_event(Event.END_GAME)
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


def draw_x(state, number_of_cards, next_state):
    if "deck" not in state or not state["deck"] or len(state["deck"]) < number_of_cards:
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
    state["game_state"] = next_state
    state["community_cards"] = state["community_cards"] + [state["deck"].pop(0) for _ in range(0, number_of_cards)]

    event = None
    if all_players_all_in(state):
        state["players"][next_player_id]["state"] = PlayerState.IN_GAME
        event = next_state_event(next_state)

    return event, state


def draw_flop(state):
    return draw_x(state, 3, GameState.FLOP)


def draw_river(state):
    return draw_x(state, 1, GameState.RIVER)


def draw_turn(state):
    return draw_x(state, 1, GameState.TURN)


def player_call(state, player_id):
    validate_check_or_call_or_fold(state, player_id)

    if all_aligned(state):
        return player_check(state, player_id)

    current_player = state["players"][player_id]
    max_bet = get_max_bet(state)
    if current_player["committed_by"] < max_bet:
        if state["game_type"] == "drinking" or state["players_stacks"][player_id] > max_bet:
            current_player["committed_by"] = max_bet
        else:
            current_player["committed_by"] = state["players_stacks"][player_id]

    (players_after_current_not_folded,
     players_before_current_not_folded_not_aligned) = determine_next_players_for_this_round(state, player_id)

    state["players"][player_id]["state"] = PlayerState.IN_GAME
    event = None

    bing_blind_called_and_turn_to_big_blind = (
        len(players_after_current_not_folded) == 1
        and state["players"][players_after_current_not_folded[0]]["committed_by"] == state["big_blind"]
    )

    if all_players_all_in(state) or (all_aligned(state) and not bing_blind_called_and_turn_to_big_blind):
        event = next_state_event(state["game_state"])
    elif players_after_current_not_folded:
        state["players"][players_after_current_not_folded[0]]["state"] = PlayerState.MY_TURN
    elif players_before_current_not_folded_not_aligned:
        state["players"][players_before_current_not_folded_not_aligned[0]]["state"] = PlayerState.MY_TURN
    else:
        event = next_state_event(state["game_state"])

    return event, state


def best_combination(cards) -> Result:
    def get_sequences_in_len_reversed_order(
            ordered_cards,
            are_following_each_other,
            skip_if=lambda card1, card2: False
    ):
        sequences = [[ordered_cards[0]]]
        for card in ordered_cards[1:]:
            if are_following_each_other(sequences[-1][-1], card):
                sequences[-1].append(card)
            elif skip_if(sequences[-1][-1], card):
                pass
            else:
                sequences.append([card])
        return sorted(sequences, key=lambda seq: len(seq), reverse=True)

    def get_longest_sequence(ordered_cards, are_following_each_other, skip_if=lambda card1, card2: False):
        sequences = get_sequences_in_len_reversed_order(ordered_cards, are_following_each_other, skip_if=skip_if)
        return sequences[0]

    def check_straight_flush(ordered_cards):
        longest_straight_flush_sequence = get_longest_sequence(
            ordered_cards,
            lambda card1, card2: card1.value == card2.value + 1 and card1.suit == card2.suit
        )
        if len(longest_straight_flush_sequence) >= 5:
            return Result(
                Combinations.STRAIGHT_FLUSH,
                (max([card.value for card in longest_straight_flush_sequence]),)
            )

    def check_four_of_a_kind(ordered_cards):
        longest_same_value_sequence = get_longest_sequence(
            ordered_cards,
            lambda card1, card2: card1.value == card2.value
        )
        if len(longest_same_value_sequence) == 4:
            value = longest_same_value_sequence[0].value
            return Result(
                Combinations.FOUR_OF_A_KIND,
                (value,
                 max({card.value for card in ordered_cards} - {value}))
            )

    def check_full_house(ordered_cards):
        same_card_sequences = get_sequences_in_len_reversed_order(
            ordered_cards,
            lambda card1, card2: card1.value == card2.value
        )
        if len(same_card_sequences[0]) == 3 and len(same_card_sequences[1]) >= 2:
            return Result(
                Combinations.FULL_HOUSE,
                (same_card_sequences[0][0].value, same_card_sequences[1][0].value)
            )

    def check_flush(ordered_cards):
        longest_same_suit_sequence = get_longest_sequence(
            sorted(ordered_cards, key=lambda card: card.suit),
            lambda card1, card2: card1.suit == card2.suit
        )
        if len(longest_same_suit_sequence) >= 5:
            return Result(
                Combinations.FLUSH,
                tuple([card.value for card in longest_same_suit_sequence][0:5])
            )

    def check_straight(ordered_cards):
        longest_sequence = get_longest_sequence(
            ordered_cards,
            lambda card1, card2: card1.value == card2.value + 1,
            skip_if=lambda card1, card2: card1.value == card2.value
        )
        if len(longest_sequence) >= 5:
            return Result(
                Combinations.STRAIGHT,
                (longest_sequence[0].value,)
            )

    def check_three_of_a_kind(ordered_cards):
        longest_same_card_sequence = get_longest_sequence(
            ordered_cards,
            lambda card1, card2: card1.value == card2.value
        )
        if len(longest_same_card_sequence) == 3:
            value_of_triplet = longest_same_card_sequence[0].value
            return Result(
                Combinations.THREE_OF_A_KIND,
                (longest_same_card_sequence[0].value,) +
                tuple(sorted(list(
                    {card.value for card in ordered_cards} - {value_of_triplet}
                ), reverse=True)[0:2])
            )

    def check_two_pairs(ordered_cards):
        longest_same_card_sequences = get_sequences_in_len_reversed_order(
            ordered_cards,
            lambda card1, card2: card1.value == card2.value
        )
        two_cards_sequences_in_reverse_value_order = sorted(
            filter(lambda seq: len(seq) == 2, longest_same_card_sequences),
            key=lambda seq: seq[0].value,
            reverse=True
        )
        if len(two_cards_sequences_in_reverse_value_order) >= 2:
            highest_pair_value = two_cards_sequences_in_reverse_value_order[0][0].value
            second_highest_pair_value = two_cards_sequences_in_reverse_value_order[1][0].value
            all_values = {card.value for card in ordered_cards}
            return Result(
                Combinations.TWO_PAIRS,
                (
                    highest_pair_value,
                    second_highest_pair_value,
                    max(all_values - {highest_pair_value, second_highest_pair_value})
                )
            )

    def check_one_pair(ordered_cards):
        longest_same_card_sequences = get_sequences_in_len_reversed_order(
            ordered_cards,
            lambda card1, card2: card1.value == card2.value
        )
        if len(longest_same_card_sequences[0]) == 2:
            pair_value = longest_same_card_sequences[0][0].value
            three_best_single_card_values = tuple(sorted(
                {card.value for card in ordered_cards} - {pair_value},
                reverse=True
            )[0:3])
            return Result(
                Combinations.ONE_PAIR,
                (pair_value,) + three_best_single_card_values
            )

    cards_in_order = sorted([Card(*card) for card in cards], reverse=True)

    for check_combination in [
        check_straight_flush,
        check_four_of_a_kind,
        check_full_house,
        check_flush,
        check_straight,
        check_three_of_a_kind,
        check_two_pairs,
        check_one_pair
    ]:
        combination = check_combination(cards_in_order)
        if combination:
            return combination

    return Result(
        Combinations.HIGH_CARD,
        tuple(sorted([card.value for card in cards_in_order], reverse=True)[0:5])
    )


def end_game(state):
    state["game_state"] = GameState.GAME_OVER
    state["results"] = generate_end_game_results(state)
    if state["game_type"] == "normal":
        return Event.make_event(Event.RESOLVE_STACKS), state
    return None, state


def deal_pot(ranking, commits, players_stacks, pot):
    if pot == 0 or ranking == []:
        return

    winners_ids = ranking[0]

    smallest_winner = sorted(
        winners_ids,
        key=lambda w_id: commits[w_id],
        reverse=True
    )[0]
    smallest_winner_commit = commits[smallest_winner]

    smallest_winner_pot = 0
    for _ in commits:  # Read "for _ in players" but we don't have access to players here
        pot_pull = smallest_winner_commit if smallest_winner_commit <= pot else pot
        pot = pot - pot_pull
        smallest_winner_pot = smallest_winner_pot + min(smallest_winner_commit, pot_pull)

    for winner_id in winners_ids:
        players_stacks[winner_id] += int(smallest_winner_pot/len(winners_ids))

    ranking[0].remove(smallest_winner)
    del commits[smallest_winner]
    if not ranking[0]:
        ranking = ranking[1:]
    deal_pot(
        ranking,
        commits,
        players_stacks,
        pot
    )


def resolve_stacks(state):
    if state["game_state"] != GameState.GAME_OVER:
        raise EventRejected("Trying to resolve stacks for a game that is not over")

    players = state["players"]
    players_stacks = state["players_stacks"]
    for player_id in players:
        players_stacks[player_id] -= players[player_id]["committed_by"]

    # Now deal the pot
    pot = sum(players[player_id]["committed_by"] for player_id in players)
    commits = {
        player_id: players[player_id]["committed_by"]
        for player_id in players
        if "committed_by" in players[player_id]
    }

    deal_pot(copy.deepcopy(state["results"]["ranking"]), commits, players_stacks, pot)

    players_at_0_stack = [player_id for player_id in players if players_stacks[player_id] == 0]

    return (
        ({"type": Event.PLAYERS_LOST, "players_ids": players_at_0_stack}
         if players_at_0_stack
         else None),
        state
    )


def get_raise_limit(state, player_id):
    if state["game_type"] == "normal":
        return state["players_stacks"][player_id]
    else:
        return state["all_in"]


def player_raise(state, player_id, amount):

    def committed_by_or_0():
        if "committed_by" in state["players"][player_id]:
            return state["players"][player_id]["committed_by"]
        else:
            return 0

    new_committed_by = amount if state["game_type"] != "normal" else (amount + committed_by_or_0())

    if player_id not in state["players"]:
        raise EventRejected(f"Unknown player {player_id} trying to raise")
    elif state["players"][player_id]["state"] != PlayerState.MY_TURN:
        raise EventRejected(f"Player {player_id} trying to raise while not their turn")
    elif new_committed_by <= get_max_bet(state):
        raise EventRejected(f"Player {player_id} trying to raise under max bet")
    elif new_committed_by > get_raise_limit(state, player_id):
        raise EventRejected(f"Player {player_id} trying to raise over limit")

    state["players"][player_id]["committed_by"] = new_committed_by

    (players_after_current_not_folded,
     players_before_current_not_folded_not_aligned) = determine_next_players_for_this_round(state, player_id)

    state["players"][player_id]["state"] = PlayerState.IN_GAME
    next_player_id = (
        players_after_current_not_folded[0] if players_after_current_not_folded
        else players_before_current_not_folded_not_aligned[0]
    )
    state["players"][next_player_id]["state"] = PlayerState.MY_TURN

    return None, state


def show_cards(state, player_id):
    if player_id not in state["players"]:
        raise EventRejected(f"Trying to show cards for player {player_id}, who's not in the game")
    state["players"][player_id]["show_cards"] = True
    return None, state


def players_lost(state, players_ids: List[str]):
    # reset stacks of losers
    for looser_id in players_ids:
        state["players_stacks"][looser_id] = 1000
    return (
        {
            "type": Event.MULTI_EVENT,
            "events": [
                {"type": Event.PLAYER_LEAVE,
                 "player_id": looser_id}
                for looser_id in players_ids
            ]
        },
        state
    )


def process_event(state, event):
    """
    Event loop.
    Event are processed, and if the processing of an event generates an event, then it is processed too before
    returning to the caller (recursive).
    Note that it processes MULTI_EVENTs, which combines one or more events, in a list. In that case itill process the
    first event of the list, and all the events it generates, then move on to processing the second and all the events
    the processing generates, then ...
    """
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
    elif event["type"] == Event.DRAW_RIVER:
        event, new_state = draw_river(state)
    elif event["type"] == Event.DRAW_TURN:
        event, new_state = draw_turn(state)
    elif event["type"] == Event.CALL:
        event, new_state = player_call(
            state,
            event["player_id"]
        )
    elif event["type"] == Event.RAISE:
        event, new_state = player_raise(
            state,
            event["player_id"],
            event["parameters"]["amount"],
        )
    elif event["type"] == Event.END_GAME:
        event, new_state = end_game(state)
    elif event["type"] == Event.SHOW_CARDS:
        event, new_state = show_cards(
            state,
            event["player_id"]
        )
    elif event["type"] == Event.RESOLVE_STACKS:
        event, new_state = resolve_stacks(state)
    elif event["type"] == Event.PLAYERS_LOST:
        event, new_state = players_lost(state, event["players_ids"])
    elif event["type"] == Event.MULTI_EVENT:
        new_state = state
        for one_event in event["events"]:
            new_state = process_event(new_state, one_event)
        event = None
    else:
        print(f"WARNING: unknown event type: {event['type']}")
        event, new_state = None, state

    if event:
        return process_event(new_state, event)
    else:
        return new_state
