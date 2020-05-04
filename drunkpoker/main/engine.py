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


class GameState:
    NOT_STARTED = "NOT_STARTED"
    PREFLOP = "PREFLOP"


class Suit:
    SPADE = "SPADE",
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
            "1": {},
            "2": {},
            "3": {},
            "4": {},
            "5": {},
            "6": {},
            "7": {},
            "8": {},
            "9": {},
            "10": {}
        },
        'turn_to': -1,
        'players': {},
        'game_state': GameState.NOT_STARTED,
        'dealing': ''
    }


class EventProcessingFailed(Exception):

    def __init__(self, explanation):
        self.explanation = explanation


class Event(Enum):
    PLAYER_SIT = auto()


def determine_next_dealer(state):
    current_dealer = state["dealing"]
    occupied_seats_in_order = [
        seat_number
        for seat_number in state["seats"]
        if state["seats"][seat_number]
    ]
    if current_dealer and state["seats"][current_dealer]:
        return str(
            (occupied_seats_in_order[int(current_dealer) % len(state["seats"])])
        )
    else:
        return occupied_seats_in_order[0]


def start_game(state):

    def rotate(l, n):
        return l[n:] + l[:n]

    for player_id in state["players"]:
        state["players"][player_id]["state"] = PlayerState.IN_GAME

    state["dealing"] = determine_next_dealer(state)
    state["deck"] = shuffle_deck()
    sitted_players_ids = [
        player_id
        for (seat_number, player_id) in state["seats"].items()
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
        sitted_players_ids_starting_after_dealer[-3 % len(sitted_players_ids_starting_after_dealer)]
    ]["committed_by"] = state["big_blind"]
    return state


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
        # Start the game
        state = start_game(state)

    return state


def process_event(state, event):
    if event["type"] == Event.PLAYER_SIT:
        return sit_player(
            state,
            event["player_id"],
            event["parameters"]["player_name"],
            event["parameters"]["seat_number"]
        )

