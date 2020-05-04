import pytest
import copy
from unittest import mock

from drunkpoker.main import engine
from drunkpoker.main.engine import Card
from drunkpoker.main.engine import Suit


@pytest.fixture
def shuffled_test_deck():
    # 4 As on top!
    return tuple([
        Card(14, Suit.SPADE),
        Card(14, Suit.DIAMONDS),
        Card(14, Suit.HEART),
        Card(14, Suit.CLUBS),
        Card(2, Suit.HEART),
        Card(3, Suit.SPADE)
    ])


@pytest.fixture
def empty_table():
    return {
        'deck': engine.deck,
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
        'dealing': "",
        'players': {},
        'game_state': engine.GameState.NOT_STARTED,
        'small_blind': 1,
        'big_blind': 2
    }


@pytest.fixture
def table_with_one_player():
    return {
        'deck': engine.deck,
        'flop': [],
        'seats': {
            "1": "",
            "2": "",
            "3": "abcd1234",
            "4": "",
            "5": "",
            "6": "",
            "7": "",
            "8": "",
            "9": "",
            "10": ""
        },
        'dealing': "",
        'players': {
            "abcd1234": {
                "name": "Quentin",
                "state": engine.PlayerState.WAITING_NEW_GAME
            }
        },
        'game_state': engine.GameState.NOT_STARTED,
        'small_blind': 1,
        'big_blind': 2
    }


@pytest.fixture
def ongoing_game():
    return {
        'deck': engine.deck,
        'flop': [],
        'seats': {
            "1": "",
            "2": "",
            "3": "abcd1234",
            "4": "other_id",
            "5": "",
            "6": "",
        },
        'dealing': "3",
        'players': {
            "abcd1234": {
                "Doesn't": "matter"
            },
            "other_id": {
                "Doesn't": "matter"
            }
        },
        'game_state': engine.GameState.PREFLOP,
        'small_blind': 1,
        'big_blind': 2
    }


def test_sit_player_on_empty_table(empty_table, table_with_one_player):
    assert engine.sit_player(
        empty_table,
        "abcd1234",
        "Quentin",
        3
    ) == table_with_one_player


def test_sit_on_occupied_seat(table_with_one_player):
    with pytest.raises(engine.EventRejected):
        engine.sit_player(
            table_with_one_player,
            "lolazerty",
            "Paul",
            "3"
        )


def test_sit_twice(table_with_one_player):
    with pytest.raises(engine.EventRejected):
        engine.sit_player(
            table_with_one_player,
            "abcd1234",
            "Paul",
            "5"
        )


def test_mock_shuffle_deck():
    with mock.patch('drunkpoker.main.engine.shuffle_deck') as mock_shuffle:
        mock_shuffle.return_value = "I have been mocked"
        assert engine.shuffle_deck() == "I have been mocked"


def test_sit_on_table_with_one_player(table_with_one_player, shuffled_test_deck):

    with mock.patch('drunkpoker.main.engine.shuffle_deck') as mock_shuffle:
        mock_shuffle.return_value = list(shuffled_test_deck)
        new_state = engine.sit_player(
            table_with_one_player,
            "wxyz6789",
            "Paul",
            "5"
        )
        assert new_state["deck"] == list(shuffled_test_deck[4:])
        assert new_state["game_state"] == engine.GameState.PREFLOP
        assert new_state["seats"]["5"] == "wxyz6789"
        assert new_state["dealing"] == "3"
        assert "wxyz6789" in new_state["players"]
        assert new_state["players"]["abcd1234"] == {
            "state": engine.PlayerState.IN_GAME,
            "name": "Quentin",
            "committed_by": new_state["big_blind"],
            "cards": list(shuffled_test_deck[0:2])
        }
        assert new_state["players"]["wxyz6789"] == {
            "state": engine.PlayerState.MY_TURN,
            "name": "Paul",
            "committed_by": new_state["small_blind"],
            "cards": list(shuffled_test_deck[2:4])  # Not a conventional way of dealing but w/e
        }
        assert new_state["dealing"] == "3"
        assert new_state["flop"] == []


def test_sit_on_ongoing_game(ongoing_game):
    saved_state = copy.deepcopy(ongoing_game)
    new_state = engine.sit_player(
        ongoing_game,
        "wxyz6789",
        "Paul",
        "5"
    )
    assert new_state["players"]["wxyz6789"] == {
        "state": engine.PlayerState.WAITING_NEW_GAME,
        "name": "Paul"
    }
    assert new_state["seats"]["5"] == "wxyz6789"
    # Checking nothing else change by reverting "by hand"
    del new_state["players"]["wxyz6789"]
    new_state["seats"]["5"] = ""
    assert new_state == saved_state


class TestDetermineNextDealer:

    def test_determine_next_dealer_full_table(self):
        state = {
            "dealing": "2",
            "seats": {
                "1": "playerX",
                "2": "playerY",
                "3": "playerZ",
            }
        }
        assert engine.determine_next_dealer(state) == "3"

    def test_determine_next_dealer_table_with_hole(self):
        state = {
            "dealing": "1",
            "seats": {
                "1": "playerX",
                "2": "",
                "3": "playerY",
            }
        }
        assert engine.determine_next_dealer(state) == "3"

    def test_determine_next_dealer_from_last_seat(self):
        state = {
            "dealing": "3",
            "seats": {
                "1": "playerX",
                "2": "",
                "3": "playerY",
            }
        }
        assert engine.determine_next_dealer(state) == "1"

    def test_determine_next_dealer_from_last_seat_with_hole(self):
        state = {
            "dealing": "3",
            "seats": {
                "1": "",
                "2": "playerX",
                "3": "playerY",
            }
        }
        assert engine.determine_next_dealer(state) == "2"

    def test_determine_dealer_with_no_current_dealer(self):
        state = {
            "dealing": "",
            "seats": {
                "1": "",
                "2": "playerX",
                "3": "playerY",
            }
        }
        assert engine.determine_next_dealer(state) == "2"

    def test_determine_dealer_current_dealer_not_here(self):
        state = {
            "dealing": "1",
            "seats": {
                "1": "",
                "2": "playerX",
                "3": "playerY",
            }
        }
        assert engine.determine_next_dealer(state) == "2"
