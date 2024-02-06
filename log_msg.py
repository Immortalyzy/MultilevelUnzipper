""" logging functions for the application """
from datetime import datetime
from setting import Config

settings = Config.get_instance().settings


# log function, its settings are controlled by global variables
def log_msg(message, log_level=3):
    """log the message to the console and optionally to a file, automatically add time stamp"""
    # log levels 1=tiny, 2=detailed, 3=normal, 4=important, 5=critical
    if log_level >= settings["log_level"]:
        time_message = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " "
        for _ in range(log_level):
            time_message += "-"
        time_message += " " + message

        if settings["log_to_file"]:
            with open(settings["log_file_name"], "a") as f:
                f.write(time_message + "\n")
        else:
            print(time_message)
