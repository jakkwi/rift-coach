from rift_coach.champselect import parse_session


def test_parses_my_turn(session_my_turn, champion_name):
    draft = parse_session(session_my_turn, champion_name)

    assert draft.my_position == "middle"
    assert draft.my_turn_to_pick is True
    assert draft.my_locked is False
    assert draft.my_champion == "Ahri"  # hovered via championPickIntent
    assert sorted(draft.enemies) == ["Lee Sin", "Zed"]
    assert draft.bans == ["Darius", "Orianna", "Swain", "Yasuo"]


def test_unavailable_excludes_my_own_hover(session_my_turn, champion_name):
    draft = parse_session(session_my_turn, champion_name)
    unavailable = draft.unavailable()

    assert "Ahri" not in unavailable
    assert {"Garen", "Vi", "Zed", "Lee Sin", "Orianna"} <= unavailable


def test_lock_in_detected(session_my_turn, champion_name):
    for group in session_my_turn["actions"]:
        for action in group:
            if action["actorCellId"] == 2:
                action.update(completed=True, isInProgress=False)
    session_my_turn["myTeam"][2]["championId"] = 103

    draft = parse_session(session_my_turn, champion_name)
    assert draft.my_locked is True
    assert draft.my_turn_to_pick is False


def test_no_summoner_names_in_state(session_my_turn, champion_name):
    session_my_turn["myTeam"][0]["gameName"] = "SomeoneElse"
    draft = parse_session(session_my_turn, champion_name)
    assert "SomeoneElse" not in repr(draft)
