class BaseWsUserData:
    def __init__(self, api_key, secret_key, rebalancer, client, shutdown_event, handler=None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.client = client
        self.shutdown_event = shutdown_event
        self.handler = handler
        self.rebalancer = rebalancer

    async def connect(self):
        raise NotImplementedError