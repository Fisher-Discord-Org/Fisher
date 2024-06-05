from discord.app_commands import errors


class UserNotOwner(errors.CheckFailure):
    def __init__(self, messsage="You are not the owner of the bot."):
        self.message = messsage
        super().__init__(self.message)


class UserBlackListed(errors.CheckFailure):
    def __init__(self, message="You are blacklisted from using the bot."):
        self.message = message
        super().__init__(self.message)


class ModuleCommandException(errors.CommandInvokeError):
    def __init__(self, log_message: str, user_message: str, module_name: str):
        super().__init__(log_message)
        self.user_message = user_message
        self.module_name = module_name


class CommandArgumentError(errors.AppCommandError):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


class FisherExitCommand(errors.AppCommandError):
    pass
