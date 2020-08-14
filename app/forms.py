from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo

from app.models.base import User

MINIMUM_PASSWORD_LENGTH = 10
REMINDER_DEFAULT = "Implementation intentions are an effective way to change behavior:\n\n" \
                   "In situation X, I will do behavior Y to achieve subgoal Z."


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me', default="checked")
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    # When you add any methods that match the pattern validate_<field_name>, WTForms takes those as custom validators
    # and invokes them in addition to the stock validators.
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Username already registered; please use a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('There is a user with that email address already registered. '
                                  'Want to <a href="login">log in</a> instead?')

    def validate_password(self, password):
        if len(password.data) < MINIMUM_PASSWORD_LENGTH:
            raise ValidationError(f'Please pick a password that is at least {MINIMUM_PASSWORD_LENGTH} characters long.')


class ReminderForm(FlaskForm):
    title = StringField('Title:', validators=[DataRequired()])
    message = TextAreaField('Message:', validators=[DataRequired()], default=REMINDER_DEFAULT)
    submit = SubmitField('Add reminder')
