# Changelog

## 2026-05-04 - Logan

### TLDR
- added puzzle to home page, didn't do anything to matches, merged all settings onto one page, some ui changes, hard coded sample user(delete before deployment)

### Notable Files Removed

- `web-app/templates/profile.html` - merged with Settings.
- `web-app/templates/puzzle_questions.html` - Reason: puzzle answers moved back into Setup.

### Notable Files Added

- `docker-compose.yml`
  - New Compose setup for web app, game engine, and MongoDB.

- `.env.example`
  - Documents expected environment variables.

- `CHANGELOG.md`
  - Tracks local changes without version tags.

### Changes

- Added game-engine puzzle board to Dashboard.
- Replaced Dashboard question/answer inputs with Boggle-style board guessing.
- Reduced navbar and hid protected nav until authentication.
- Brand link sends logged-in users to Dashboard.
- Merged Profile into Settings.
- Moved logout from navbar to Settings.
- Settings now edits user info, password, and profile image.
- Profile image circle is clickable and replaces the visible file input.
- Setup now edits profile details and puzzle answers.
- Settings has an `Edit puzzle answers` button that links to Setup.
- Added readable puzzle-generation errors.
- Added hard-coded `sample_match` seed user for local testing.
- Added centered card layout and Boggle board styling.
- Added Docker live reload for `web-app`.
- Updated route docs and pytest cache settings.

### TODO Before Deployment

- Remove hard-coded `sample_match` user and answers.
- Replace `SECRET_KEY=changeme`.
- Disable Flask debug/live reload.
- Decide whether MongoDB should expose host port `27017`.


### Potential Future Addition:
- custom questions - allow ability to substitute with custom questions
- implement direct messages with matches
- change default questions (which is current kind bad) and potentially shorten to less questions
- support longer answers