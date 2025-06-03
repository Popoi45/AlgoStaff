class BaseWs:
    def __init__(self, shutdown_event, topics, handler=None):
        self.shutdown_event = shutdown_event
        self.handler = handler
        self.topics = topics

    async def connect(self):
        raise NotImplementedError