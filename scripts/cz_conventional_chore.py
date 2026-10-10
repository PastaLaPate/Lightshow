from typing import cast

from commitizen.cz.conventional_commits import ConventionalCommitsCz
from commitizen.question import ListQuestion


class ConventionalChoreCz(ConventionalCommitsCz):
    def questions(self):
        questions = super().questions()
        for q in questions:
            if q["name"] == "prefix":  # the "type of change" question
                choices_q = cast(ListQuestion, q)
                choices_q["choices"].append(
                    {
                        "value": "chore",
                        "name": "chore: Maintenance, tooling, misc",
                        "key": "o",
                    }
                )
        return questions
