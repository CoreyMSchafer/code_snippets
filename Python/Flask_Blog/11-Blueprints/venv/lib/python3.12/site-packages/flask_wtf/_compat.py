import warnings


class FlaskWTFDeprecationWarning(DeprecationWarning):
    pass


warnings.simplefilter("always", FlaskWTFDeprecationWarning)
warnings.filterwarnings(
    "ignore", category=FlaskWTFDeprecationWarning, module="wtforms|flask_wtf"
)
