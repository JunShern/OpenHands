import ast

from openhands.controller.action_parser import ActionParser, ResponseParser
from openhands.core.logger import openhands_logger as logger
from openhands.events.action import (
    Action,
    BrowseInteractiveAction,
)


class BrowsingResponseParser(ResponseParser):
    def __init__(self):
        # Need to pay attention to the item order in self.action_parsers
        super().__init__()
        self.action_parsers = [BrowsingActionParserMessage()]
        self.default_parser = BrowsingActionParserBrowseInteractive()

    def parse(self, response: str) -> Action:
        action_str = self.parse_response(response)
        return self.parse_action(action_str)

    def parse_response(self, response) -> str:
        action_str = response['choices'][0]['message']['content']
        if action_str is None:
            return ''
        action_str = action_str.strip()
        if action_str and not action_str.endswith('```'):
            action_str = action_str + ')```'
        logger.debug(action_str)
        return action_str

    def parse_action(self, action_str: str) -> Action:
        for action_parser in self.action_parsers:
            if action_parser.check_condition(action_str):
                return action_parser.parse(action_str)
        return self.default_parser.parse(action_str)


class BrowsingActionParserMessage(ActionParser):
    """Parser action:
    - BrowseInteractiveAction(browser_actions) - unexpected response format, message back to user
    """

    def __init__(
        self,
    ):
        pass

    def check_condition(self, action_str: str) -> bool:
        return '```' not in action_str

    def parse(self, action_str: str) -> Action:
        msg = "send_msg_to_user({})".format(repr(action_str))
        return BrowseInteractiveAction(
            browser_actions=msg,
            thought=action_str,
            browsergym_send_msg_to_user=action_str,
        )


class BrowsingActionParserBrowseInteractive(ActionParser):
    """Parser action:
    - BrowseInteractiveAction(browser_actions) - handle send message to user function call in BrowserGym
    """

    def __init__(
        self,
    ):
        pass

    def check_condition(self, action_str: str) -> bool:
        return True

    def parse(self, action_str: str) -> Action:
        # parse the action string into browser_actions and thought
        # the LLM can return only one string, or both

        # when both are returned, it looks like this:
        ### Based on the current state of the page and the goal of finding out the president of the USA, the next action should involve searching for information related to the president.
        ### To achieve this, we can navigate to a reliable source such as a search engine or a specific website that provides information about the current president of the USA.
        ### Here is an example of a valid action to achieve this:
        ### ```
        ### goto('https://www.whitehouse.gov/about-the-white-house/presidents/'
        # in practice, BrowsingResponseParser.parse_response also added )``` to the end of the string

        # when the LLM returns only one string, it looks like this:
        ### goto('https://www.whitehouse.gov/about-the-white-house/presidents/')
        # and parse_response added )``` to the end of the string
        parts = action_str.split('```')
        browser_actions = (
            parts[1].strip() if parts[1].strip() != '' else parts[0].strip()
        )
        thought = parts[0].strip() if parts[1].strip() != '' else ''

        # if the LLM wants to talk to the user, we extract the message
        msg_content = ''
        for sub_action in browser_actions.split('\n'):
            if 'send_msg_to_user(' in sub_action:
                tree = ast.parse(sub_action)
                args = tree.body[0].value.args  # type: ignore
                msg_content = args[0].value

        return BrowseInteractiveAction(
            browser_actions=browser_actions,
            thought=thought,
            browsergym_send_msg_to_user=msg_content,
        )
