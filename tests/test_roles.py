from rift_coach.roles import load_viable

ROLES = {"top", "jungle", "middle", "bottom", "utility"}


def test_bundled_file_has_all_roles():
    viable = load_viable()
    assert set(viable) == ROLES
    assert all(len(v) >= 20 for v in viable.values())


def test_no_duplicates_within_role():
    for role, names in load_viable().items():
        assert len(names) == len(set(names)), role


def test_resolves_against_data_dragon_names():
    text = 'middle = ["ahri", "LeBlanc", "Notachampion"]\n'
    out = load_viable(["Ahri", "LeBlanc", "Syndra"], text=text)
    assert out["middle"] == ["Ahri", "LeBlanc"]


def test_swain_is_not_top():
    assert "Swain" not in load_viable()["top"]
