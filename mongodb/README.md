This directory contains the MongoDB subsystem for the project.

Schemas
User:
* profile pic // upload image
* question/answer pair
* age
* gender
* username
* password
* email
* array of matched users (object)


User
```js
{
  _id: ObjectId,
  email: "morgan@example.com",
  password_hash: "...",
  username: "morgan",
  age: 22,
  gender: "Not set",
  profile_pic: "https://...",
  questions: [
    {
      question: "Favorite music genre?",
      answer: "Jazz"
    },
    {
      question: "Dream travel spot?",
      answer: "Germany"
    }
  ]
}
```