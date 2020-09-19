



class EventManager:
    """
    Collect all functions from each module where Registrator has been initialized
    """
    SUBSCRIPTIONS = {}

    @staticmethod
    def subscribe(subsciption: list or str, serializator: type):
        def wrapper(function):
            function = EventManager.wrap_function_by_serializer(function, serializator)
            if type(subsciption) is list:
                for s in subsciption:
                    EventManager._check_subscription(s)
                    EventManager.SUBSCRIPTIONS[s].append(function)
            else:
                EventManager._check_subscription(subsciption)
                EventManager.SUBSCRIPTIONS[subsciption].append(function)
            return function
        return wrapper

    @staticmethod
    def wrap_function_by_serializer(function, serializator):
        def wrapper(topic, message):
            try:
                message = serializator.validate_message(message)
            except Exception as e:
                raise Exception(str(e))
            return function(topic, message)

        return wrapper

    @staticmethod
    def _check_subscription(subsciption):
        if not subsciption in EventManager.SUBSCRIPTIONS:
            EventManager.SUBSCRIPTIONS[subsciption] = []

    def get_topics_and_callbacks(self):
        topics_callbacks = {}
        for topic, events in EventManager.SUBSCRIPTIONS.items():
            topics_callbacks[topic] = events
        return topics_callbacks

