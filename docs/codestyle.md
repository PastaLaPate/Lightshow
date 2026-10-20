# Codestyle

Try to follow the following guidelines:

## Variables name

Use @property when needs to listen to when the variable changed, the internal value will be stored in self.\_variable_name.
When in QT Components, ui-like properties need to follow QT's standards: setters and getters like getText(), setText(value: str) or text()

## Functions

Annotate as much as possible and as narrower as possible types.
