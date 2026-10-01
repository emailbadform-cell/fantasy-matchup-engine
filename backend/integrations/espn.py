class ESPNClient:
    """Secure integration boundary for ESPN.

    Credentials/session material will be supplied through secure runtime
    configuration only. Nothing sensitive belongs in source control.
    """

    def __init__(self, session=None):
        self.session = session

    def list_leagues(self):
        raise NotImplementedError
