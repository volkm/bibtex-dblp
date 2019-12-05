import logging


def get_user_input(message):
    """
    Get input from user.
    :param message: Message to display.
    :return: User input.
    """
    return input(message)


def get_user_number(message, val_min=None, val_max=None):
    """
    Get number from user input. If the input is not a valid number, the user is asked again.
    :param message: Message to print.
    :param val_min: Minimal value required for input. If None, no minimal bound is given.
    :param val_max: Maximal value required for output. If None, no maximal bound is given.
    :return: Number given by user.
    """
    while True:
        inp = get_user_input(message)
        try:
            inp_number = int(inp)
        except ValueError:
            logging.error("The input is not a number.")
        else:
            if val_min is not None and inp_number < val_min:
                logging.error("The input must be at least {}.".format(val_min))
            elif val_max is not None and inp_number > val_max:
                logging.error("The input must be at most {}.".format(val_max))
            else:
                # Number is valid
                return inp_number
