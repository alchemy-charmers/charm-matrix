import os
import pytest
import subprocess
import stat

# Treat all tests as coroutines
pytestmark = pytest.mark.asyncio

juju_repository = os.getenv("JUJU_REPOSITORY", ".").rstrip("/")
series = [
    "xenial",
    "bionic",
    pytest.param("eoan", marks=pytest.mark.xfail(reason="canary")),
]
sources = [
    ("local", "{}/builds/matrix".format(juju_repository)),
    # ('jujucharms', 'cs:...'),
]


# Custom fixtures
@pytest.fixture(params=series)
def series(request):
    return request.param


@pytest.fixture(params=sources, ids=[s[0] for s in sources])
def source(request):
    return request.param


@pytest.fixture
async def app(model, series, source):
    app_name = "matrix-{}-{}".format(series, source[0])
    return await model._wait_for_new("application", app_name)


@pytest.mark.deploy
async def test_matrix_deploy(model, series, source, request):
    # Starts a deploy for each series
    # Using subprocess b/c libjuju fails with JAAS
    # https://github.com/juju/python-libjuju/issues/221
    application_name = "matrix-{}-{}".format(series, source[0])
    cmd = [
        "juju",
        "deploy",
        source[1],
        "-m",
        model.info.name,
        "--series",
        series,
        application_name,
    ]
    if request.node.get_closest_marker("xfail"):
        # If series is 'xfail' force install to allow testing against versions not in
        # metadata.yaml
        cmd.append("--force")
    subprocess.check_call(cmd)


@pytest.mark.deploy
async def test_matrix_snap_upload(model, series, source, request):
    application_name = "matrix-{}-{}".format(series, source[0])
    cmd = [
        "juju",
        "attach-resource",
        "-m",
        model.info.name,
        application_name,
        "matrix-synapse=snaps/matrix-synapse.snap"
    ]
    subprocess.check_call(cmd)


@pytest.mark.deploy
@pytest.mark.timeout(900)
async def test_charm_upgrade(model, app):
    if app.name.endswith("local"):
        pytest.skip("No need to upgrade the local deploy")
    unit = app.units[0]
    await model.block_until(lambda: unit.agent_status == "idle")
    subprocess.check_call(
        [
            "juju",
            "upgrade-charm",
            "--switch={}".format(sources[0][1]),
            "-m",
            model.info.name,
            app.name,
        ]
    )
    await model.block_until(lambda: unit.agent_status == "executing")


@pytest.mark.deploy
@pytest.mark.timeout(900)
async def test_matrix_status(model, app):
    # Verifies status for all deployed series of the charm
    await model.block_until(lambda: app.status == "active")
    unit = app.units[0]
    await model.block_until(lambda: unit.agent_status == "idle")


# Tests
async def test_register_user_action_fail(app):
    unit = app.units[0]
    action = await unit.run_action("register-user")
    action = await action.wait()
    assert action.status == "failed"


async def test_register_set_password_fail(app):
    unit = app.units[0]
    action = await unit.run_action("set-password")
    action = await action.wait()
    assert action.status == "failed"


async def test_run_command(app, jujutools):
    unit = app.units[0]
    cmd = "hostname --all-ip-addresses"
    results = await jujutools.run_command(cmd, unit)
    assert results["Code"] == "0"
    assert unit.public_address in results["Stdout"]


async def test_file_stat(app, jujutools):
    unit = app.units[0]
    path = "/var/lib/juju/agents/unit-{}/charm/metadata.yaml".format(
        unit.entity_id.replace("/", "-")
    )
    fstat = await jujutools.file_stat(path, unit)
    assert stat.filemode(fstat.st_mode) == "-rw-r--r--"
    assert fstat.st_uid == 0
    assert fstat.st_gid == 0
