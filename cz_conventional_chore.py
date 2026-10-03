from commitizen.cz.conventional_commits import ConventionalCommitsCz


class ConventionalChoreCz(ConventionalCommitsCz):
    def questions(self):
        questions = super().questions()
        for q in questions:
            if q["name"] == "prefix":  # the "type of change" question
                q["choices"].append(
                    {
                        "value": "chore",
                        "name": "chore: Maintenance, tooling, misc",
                        "key": "o",
                    }
                )
        return questions
