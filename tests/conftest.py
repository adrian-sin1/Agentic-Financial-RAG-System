import pytest


@pytest.fixture(autouse=True)
def _default_env(monkeypatch):
    """Some code paths read os.environ directly while constructing a mocked
    client's arguments (e.g. OpenAI(api_key=os.environ["OPENAI_API_KEY"])) --
    the KeyError happens while evaluating that argument, before the mock ever
    intercepts the call, since argument evaluation isn't deferred. Set a
    harmless dummy value so the test suite never depends on a real key being
    present in the environment (locally, .env quietly papers over this; CI
    has no .env file at all).
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
