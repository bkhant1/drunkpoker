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
def iddle_game_with_two_players():
    return {
        'deck': engine.deck,
        'flop': [],
        'seats': {
            "1": "",
            "2": "",
            "3": "abcd1234",
            "4": "",
            "5": "wxyz6789",
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
            },
            "wxyz6789": {
                "name": "Quentin",
                "state": engine.PlayerState.WAITING_NEW_GAME
            }
        },
        'game_state': engine.GameState.NOT_STARTED,
        'small_blind': 1,
        'big_blind': 2
    }


@pytest.fixture
def iddle_game_with_4_players_and_a_dealer():
    return {
        'deck': engine.deck,
        'flop': [],
        'seats': {
            "1": "p1",
            "2": "",
            "3": "p2",
            "4": "p3",
            "5": "",
            "6": "p4",
            "7": "",
            "8": "",
            "9": "",
            "10": ""
        },
        'dealing': "3",
        'players': {
            "p1": {
                "name": "P1",
                "state": engine.PlayerState.WAITING_NEW_GAME
            },
            "p2": {
                "name": "P2",
                "state": engine.PlayerState.WAITING_NEW_GAME
            },
            "p3": {
                "name": "P3",
                "state": engine.PlayerState.WAITING_NEW_GAME
            },
            "p4": {
                "name": "P4",
                "state": engine.PlayerState.WAITING_NEW_GAME
            }
        },
        'game_state': engine.GameState.NOT_STARTED,
        'small_blind': 1,
        'big_blind': 2
    }


@pytest.fixture
def ongoing_game_with_two_players():
    return {
        'deck': engine.deck,
        'flop': [],
        'seats': {  # Note dictionaries are unordered
            "1": "",
            "4": "other_id",
            "2": "",
            "3": "abcd1234",
            "6": "",
            "5": "",
        },
        'dealing': "3",
        'players': {
            "abcd1234": {
                "state": engine.PlayerState.MY_TURN,
                "name": "Paul",
                "committed_by": 1,
                "cards": "doesn't matter"
            },
            "other_id": {
                "state": engine.PlayerState.IN_GAME,
                "name": "Jean",
                "committed_by": 2,
                "cards": "doesn't matter"
            }
        },
        'game_state': engine.GameState.PREFLOP,
        'small_blind': 1,
        'big_blind': 2
    }


@pytest.fixture
def ongoing_game_with_three_players():
    return {
        'deck': engine.deck,
        'flop': [Card(14, engine.Suit.SPADE), Card(13, engine.Suit.SPADE), Card(12, engine.Suit.SPADE)],
        'seats': {
            "1": "",
            "2": "",
            "3": "abcd1234",
            "4": "other_id",
            "5": "",
            "6": "other_other_id",
        },
        'dealing': "3",
        'players': {
            "abcd1234": {
                "state": engine.PlayerState.MY_TURN,
                "name": "Paul",
                "committed_by": 1,
                "cards": "doesn't matter"
            },
            "other_id": {
                "state": engine.PlayerState.FOLDED,
                "name": "Jean",
                "committed_by": 2,
                "cards": "doesn't matter"
            },
            "other_other_id": {
                "state": engine.PlayerState.IN_GAME,
                "name": "Louis",
                "committed_by": 10,
                "cards": "doesn't matter"
            }
        },
        'game_state': engine.GameState.FLOP,
        'small_blind': 1,
        'big_blind': 2
    }


@pytest.fixture
def ongoing_game_with_three_players_one_waiting(ongoing_game_with_three_players):
    ongoing_game_with_three_players["players"]["other_id"]["state"] = engine.PlayerState.WAITING_NEW_GAME
    return ongoing_game_with_three_players


def test_sit_player_on_empty_table(empty_table, table_with_one_player):
    assert engine.sit_player(
        empty_table,
        "abcd1234",
        "Quentin",
        3
    ) == (None, table_with_one_player)


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


def test_sit_on_table_with_one_player(table_with_one_player):
    event, state = engine.sit_player(
        table_with_one_player,
        "helloid",
        "Jack",
        "4"
    )
    assert event == {"type": engine.Event.START_GAME}
    assert "helloid" in state["players"]
    assert len(state["players"]) == 2
    assert state["players"]["helloid"] == {
        "name": "Jack",
        "state": engine.PlayerState.WAITING_NEW_GAME
    }
    assert state["players"]["abcd1234"] == {
        "name": "Quentin",
        "state": engine.PlayerState.WAITING_NEW_GAME
    }
    assert state["seats"]["4"] == "helloid"


class TestProcessEvent:

    def test_sit_on_table_with_one_player(self, table_with_one_player, shuffled_test_deck):
        with mock.patch('drunkpoker.main.engine.shuffle_deck') as mock_shuffle:
            mock_shuffle.return_value = list(shuffled_test_deck)
            new_state = engine.process_event(
                table_with_one_player,
                {
                    "type": engine.Event.PLAYER_SIT,
                    "player_id": "wxyz6789",
                    "parameters": {
                        "player_name": "Paul",
                        "seat_number": "5"
                    }
                }
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

    def test_exclude_player_makes_game_restart(
            self,
            ongoing_game_with_three_players_one_waiting,
            shuffled_test_deck
    ):
        with mock.patch('drunkpoker.main.engine.shuffle_deck') as mock_shuffle:
            mock_shuffle.return_value = list(shuffled_test_deck)
            new_state = engine.process_event(
                ongoing_game_with_three_players_one_waiting,
                {
                    "type": engine.Event.PLAYER_LEAVE,
                    "player_id": "abcd1234"
                }
            )
        assert not new_state["seats"]["3"]
        assert new_state["dealing"] == "4"
        assert "abcd1234" not in new_state["players"]
        assert new_state["players"]["other_id"] == {
            "state": engine.PlayerState.IN_GAME,
            "name": "Jean",
            "committed_by": new_state["big_blind"],
            "cards": list(shuffled_test_deck[0:2])
        }
        assert new_state["players"]["other_other_id"] == {
            "state": engine.PlayerState.MY_TURN,
            "name": "Louis",
            "committed_by": new_state["small_blind"],
            "cards": list(shuffled_test_deck[2:4])
        }


def test_sit_on_ongoing_game(ongoing_game_with_two_players):
    saved_state = copy.deepcopy(ongoing_game_with_two_players)
    event, new_state = engine.sit_player(
        ongoing_game_with_two_players,
        "wxyz6789",
        "Paul",
        "5"
    )
    assert event is None
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

    def test_determine_next_dealer_empty_table(self):
        state = {
            "dealing": "2",
            "seats": {
                "1": "",
                "2": "",
                "3": "",
            }
        }
        with pytest.raises(engine.EventRejected):
            engine.determine_next_dealer_seat(state)

    def test_determine_next_dealer_one_player(self):
        state = {
            "dealing": "2",
            "seats": {
                "1": "",
                "2": "Paul",
                "3": "",
            }
        }
        assert engine.determine_next_dealer_seat(state) == "2"

    def test_determine_next_dealer_full_table(self):
        state = {
            "dealing": "2",
            "seats": {
                "1": "playerX",
                "2": "playerY",
                "3": "playerZ",
            }
        }
        assert engine.determine_next_dealer_seat(state) == "3"

    def test_determine_next_dealer_table_with_hole(self):
        state = {
            "dealing": "1",
            "seats": {
                "2": "",
                "3": "playerY",
                "1": "playerX"
            }
        }
        assert engine.determine_next_dealer_seat(state) == "3"

    def test_determine_next_dealer_from_last_seat(self):
        state = {
            "dealing": "3",
            "seats": {
                "1": "playerX",
                "2": "",
                "3": "playerY",
            }
        }
        assert engine.determine_next_dealer_seat(state) == "1"

    def test_determine_next_dealer_from_last_seat_with_hole(self):
        state = {
            "dealing": "3",
            "seats": {
                "1": "",
                "2": "playerX",
                "3": "playerY",
            }
        }
        assert engine.determine_next_dealer_seat(state) == "2"

    def test_determine_dealer_with_no_current_dealer(self):
        state = {
            "dealing": "",
            "seats": {
                "1": "",
                "2": "playerX",
                "3": "playerY",
            }
        }
        assert engine.determine_next_dealer_seat(state) == "2"

    def test_determine_dealer_current_dealer_not_here(self):
        state = {
            "dealing": "1",
            "seats": {
                "1": "",
                "2": "playerX",
                "3": "playerY",
            }
        }
        assert engine.determine_next_dealer_seat(state) == "2"

    def test_determine_dealer_going_full_round(self):
        state = {
            "dealing": "2",
            "seats": {
                "1": "playerY",
                "3": "",
                "2": "playerX"
            }
        }
        assert engine.determine_next_dealer_seat(state) == "1"

    @pytest.mark.parametrize("dealing, expected", [("1", "2"), ("2", "5"), ("5", "1")])
    def test_determine_dealer_big_table(self, dealing, expected):
        state = {
            "dealing": dealing,
            "seats": {
                "4": "",
                "5": "playerZ",
                "6": "",
                "1": "playerY",
                "2": "playerX",
                "3": ""
            }
        }
        assert engine.determine_next_dealer_seat(state) == expected


def test_exclude_player_game_not_started(table_with_one_player):
    event, new_state = engine.exclude_player(table_with_one_player, "abcd1234")
    assert event is None
    assert all([not player_id for player_id in new_state["seats"].values()])
    assert new_state["players"] == {}


def test_exclude_player_game_started_with_two_players(ongoing_game_with_two_players):
    event, new_state = engine.exclude_player(ongoing_game_with_two_players, "abcd1234")
    assert event is None
    assert new_state["dealing"] == ""
    assert not "abcd1234" in new_state["players"]
    assert new_state["players"]["other_id"] == {
        "state": engine.PlayerState.WAITING_NEW_GAME,
        "name": "Jean"
    }
    assert new_state["game_state"] == engine.GameState.NOT_STARTED
    assert not new_state["seats"]["3"]  # Where abcd1234 was seating


def test_exclude_player_game_started_with_three_players_her_turn_she_deals(ongoing_game_with_three_players):
    event, new_state = engine.exclude_player(ongoing_game_with_three_players, "abcd1234")
    assert event is None
    assert new_state["seats"]["3"] == ""
    assert "abcd1234" not in new_state["players"]
    assert new_state["dealing"] == "3"  # Don't change the dealer
    assert new_state["players"]["other_id"]["state"] == engine.PlayerState.MY_TURN  # player after abcd1234


def test_exclude_waiting_for_new_game_player(ongoing_game_with_three_players_one_waiting):
    next_event, new_state = engine.exclude_player(
        ongoing_game_with_three_players_one_waiting,
        "other_id"
    )
    assert next_event is None
    assert new_state["game_state"] == engine.GameState.FLOP
    assert len(new_state["players"]) == 2
    assert not new_state["seats"]["4"]
    assert new_state["players"]["abcd1234"]["state"] == engine.PlayerState.MY_TURN
    assert new_state["players"]["other_other_id"]["state"] == engine.PlayerState.IN_GAME


def test_exclude_playing_player_three_players_one_waiting(ongoing_game_with_three_players_one_waiting):
    next_event, new_state = engine.exclude_player(
        ongoing_game_with_three_players_one_waiting,
        "abcd1234"
    )
    assert next_event == {
        "type": engine.Event.START_GAME,
    }
    assert new_state["game_state"] == engine.GameState.NOT_STARTED
    assert len(new_state["players"]) == 2
    assert not new_state["seats"]["3"]
    for player_id in new_state["players"]:
        assert new_state["players"][player_id]["state"] == engine.PlayerState.WAITING_NEW_GAME


def test_exclude_player_game_started_with_three_players_not_her_turn(ongoing_game_with_three_players):
    old_state = copy.deepcopy(ongoing_game_with_three_players)
    event, new_state = engine.exclude_player(ongoing_game_with_three_players, "other_id")
    assert event is None
    del old_state["players"]["other_id"]
    assert old_state["players"] == new_state["players"]
    assert "other_id" not in new_state["seats"].values()


def test_exclude_player_that_is_not_here(ongoing_game_with_three_players):
    copy_old_state = copy.deepcopy(ongoing_game_with_three_players)
    with pytest.raises(engine.EventRejected):
        engine.exclude_player(ongoing_game_with_three_players, "I DONT EXIST")
    assert copy_old_state == ongoing_game_with_three_players


def test_exclude_in_game_player_three_players_one_of_which_waiting(
        ongoing_game_with_three_players_one_waiting,
        shuffled_test_deck
):
    event, new_state = engine.exclude_player(
        ongoing_game_with_three_players_one_waiting,
        "abcd1234"
    )
    assert event == {
        "type": engine.Event.START_GAME
    }
    assert new_state["players"]["other_id"]["state"] == engine.PlayerState.WAITING_NEW_GAME
    assert new_state["players"]["other_other_id"]["state"] == engine.PlayerState.WAITING_NEW_GAME
    assert len([seat for seat in new_state["seats"] if new_state["seats"][seat]]) == 2


def test_start_game_two_players(iddle_game_with_two_players, shuffled_test_deck):
    with mock.patch('drunkpoker.main.engine.shuffle_deck') as mock_shuffle:
        mock_shuffle.return_value = list(shuffled_test_deck)
        event, new_state = engine.start_game(
            iddle_game_with_two_players
        )
        assert event is None
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
            "name": "Quentin",
            "committed_by": new_state["small_blind"],
            "cards": list(shuffled_test_deck[2:4])  # Not a conventional way of dealing but w/e
        }
        assert new_state["dealing"] == "3"
        assert new_state["flop"] == []


def test_start_game_4_players_one_dealer(iddle_game_with_4_players_and_a_dealer):
    event, new_state = engine.start_game(
        iddle_game_with_4_players_and_a_dealer
    )
    assert event is None
    assert sum([
        1 if player["state"] == engine.PlayerState.IN_GAME else 0
        for player in new_state["players"].values()
    ]) == 3
    assert new_state["dealing"] == "4"

    big_blind_player_id = new_state["seats"]["4"]  # Dealer
    small_blind_player_id = new_state["seats"]["3"]
    assert new_state["players"][big_blind_player_id]["committed_by"] == new_state["big_blind"]
    assert new_state["players"][small_blind_player_id]["committed_by"] == new_state["small_blind"]

    assert new_state["players"]["p4"]["state"] == engine.PlayerState.MY_TURN

    assert len(new_state["deck"]) == 52 - 8
    for player in new_state["players"].values():
        assert len(player["cards"]) == 2


def test_start_game_one_player(table_with_one_player):
    old_state = copy.deepcopy(table_with_one_player)
    assert engine.start_game(table_with_one_player) == (None, old_state)


def test_start_ongoing_game(ongoing_game_with_three_players):
    # The game should restart
    event, new_state = engine.start_game(ongoing_game_with_three_players)
    assert event is None
    assert new_state["flop"] == []
    assert new_state["game_state"] == engine.GameState.PREFLOP
    assert new_state["dealing"] == "4"
    # No longer comitted
    assert "committed_by" not in new_state["players"]["other_other_id"]\
           or int(new_state["players"]["other_other_id"]["committed_by"]) == 0


class TestDetermineNextPlayer:

    def test_determine_next_player_ez_case(self):
        state = {
            "players": {
                "p1": {"state": engine.PlayerState.MY_TURN},
                "p2": {"state": engine.PlayerState.IN_GAME},
            },
            "seats": {
                "1": "p1",
                "2": "p2"
            }
        }
        assert engine.determine_next_player(state) == "p2"

    def test_determine_next_player_one_empty_seat(self):
        state = {
            "players": {
                "P1": {"state": engine.PlayerState.MY_TURN},
                "P2": {"state": engine.PlayerState.IN_GAME},
            },
            "seats": {
                "1": "P1",
                "2": "",
                "3": "P2"
            }
        }
        assert engine.determine_next_player(state) == "P2"

    def test_determine_next_player_going_round(self):
        state = {
            "players": {
                "P1": {"state": engine.PlayerState.MY_TURN},
                "P2": {"state": engine.PlayerState.IN_GAME},
            },
            "seats": {
                "1": "P2",
                "2": "P1",
                "3": ""
            }
        }
        assert engine.determine_next_player(state) == "P2"


class TestStripStateForPlayer:

    @pytest.fixture
    def state_to_strip(self):
        def ret():
            return {
                "deck": "A deck of cards",
                "players": {
                    "id1": {
                        "cards": "Some cards"
                    },
                    "id2": {
                        "cards": "Some other cards"
                    },
                    "id3": {}
    
                }
            }
        return ret

    def test_player_does_not_exist(self, state_to_strip):
        new_state = engine.strip_state_for_player(state_to_strip(), "INEXISTANT")
        assert "deck" not in new_state
        assert "cards" not in new_state["players"]["id1"]
        assert "cards" not in new_state["players"]["id2"]
        assert "cards" not in new_state["players"]["id3"]

    def test_strip_deck(self, state_to_strip):
        new_state_1, new_state_2, new_state_3 = [
            engine.strip_state_for_player(state_to_strip(), player_id)
            for player_id in ("id1", "id2", "id3")
        ]
        for new_state in (new_state_1, new_state_2, new_state_3):
            assert "deck" not in new_state

    def test_strip_other_players_cards(self, state_to_strip):
        # Strip for 1
        new_state = engine.strip_state_for_player(state_to_strip(), "id1")
        assert "cards" not in new_state["players"]["id2"]
        assert new_state["players"]["id1"]["cards"] == "Some cards"

        # Strip for 2
        new_state = engine.strip_state_for_player(state_to_strip(), "id2")
        assert "cards" not in new_state["players"]["id1"]
        assert new_state["players"]["id2"]["cards"] == "Some other cards"

        # Strip for 3
        new_state = engine.strip_state_for_player(state_to_strip(), "id3")
        assert "cards" not in new_state["players"]["id1"]
        assert "cards" not in new_state["players"]["id2"]
