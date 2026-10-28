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


def test_key_ignores_hovers(session_my_turn, champion_name):
    before = parse_session(session_my_turn, champion_name).key()
    session_my_turn["myTeam"][3]["championPickIntent"] = 222     # ally hovers Jinx
    session_my_turn["myTeam"][2]["championPickIntent"] = 134     # I hover Syndra
    assert parse_session(session_my_turn, champion_name).key() == before


def test_key_changes_on_ally_lock(session_my_turn, champion_name):
    before = parse_session(session_my_turn, champion_name).key()
    action = session_my_turn["actions"][2][1]                     # bottom's pick
    action.update(championId=222, completed=True, isInProgress=False)
    after = parse_session(session_my_turn, champion_name)
    assert after.key() != before
    assert "Jinx" in after.locked_allies


def test_pick_phase_detected(session_my_turn, champion_name):
    assert parse_session(session_my_turn, champion_name).pick_phase is True
    for group in session_my_turn["actions"]:
        for a in group:
            if a["type"] == "pick":
                a.update(completed=False, isInProgress=False)
    assert parse_session(session_my_turn, champion_name).pick_phase is False
