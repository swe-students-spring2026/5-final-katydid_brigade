This directory contains the Python web application subsystem.

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