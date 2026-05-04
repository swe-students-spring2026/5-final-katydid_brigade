This directory contains the Python web application subsystem.

## Routes

- [`GET /`](./app.py) - `home` page
- [`GET, POST /login`](./app.py) - `login` page
- [`GET, POST /register`](./app.py) - `register` page
- [`GET, POST /setup`](./app.py) - `setup` profile details and puzzle-answer editor
- [`GET, POST /dashboard`](./app.py) - `dashboard` daily challenge page
- [`GET /matches`](./app.py) - `matches_page` matched users list
- [`GET /matches/<match_id>`](./app.py) - `match_detail` matched user details
- [`GET, POST /profile`](./app.py) - `profile` compatibility redirect to settings
- [`GET, POST /setting`](./app.py) - `settings` account and profile settings
- [`GET, POST /settings`](./app.py) - `settings` compatibility alias
- [`GET, POST /setting/puzzle-questions`](./app.py) - `puzzle_questions` compatibility redirect to setup
- [`GET, POST /settings/puzzle-questions`](./app.py) - `puzzle_questions` compatibility redirect to setup
- [`GET /users/<user_id>/profile-image`](./app.py) - `profile_image` MongoDB-backed profile image
- [`GET /logout`](./app.py) - `logout` clear session and return to login



1. login pg
2. register pg
    - username/password
3. setup pg
    * user will need to fill in 10 default questions and answers (up to 10 letters)
        * ex. what's your favorite genre of music? - Jazz
        * ex. where do you want to travel? - Germany
        * ex. what's your hobby? - VibeCoding
        * etc.
    * // user also has to input basic personal information
    * save into mongodb
4. dashboard pg
    * everday, get 10 question/answer pairs from another user
        * show profile pic of the other user
        * if answer correctly on all of them, you get matched
        * we open out a new channel (or provide contact info of the matched user) in the "matches" pg
5. matches pg
    * list of matched users
        - each have a profile pic, all questions and answers, basic personal info
5. setting pg
    * change password

Schemas
User:
* profile pic
* question/answer pair
* age
* gender
* username
* password
* email


Potential Future Addition:
* custom questions - allow ability to substitute with custom questions
* implement direct messages with matches
* change default questions (which is current kind bad) and potentially shorten to less questions
* support longer answers