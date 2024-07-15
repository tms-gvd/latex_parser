Latex Parser
=

```python
python main.py
```

Then go to [http://localhost:8000/](http://localhost:8000/)

TODO:
- [x] Add a way to report issues
- [ ] Improve the parser: handle more cases, especially with the `\newcommand` and similar commands
- [ ] Add more information to the main page: title, author, date, etc.
- [ ] Display equations in the right order: it is true actually only if the paper is written in a single file
- [ ] Store the parsed data in a database to avoid parsing the same file multiple times