from jira.client import JIRA
import yaml
import getpass
import datetime
from humanfriendly import format_timespan
import re


def _remove_string_format(word):
    has_changed = False
    while word:
        if word[0] in ("{", "*", "_", "}"):
            word = word[1:]
            has_changed = True
        else:
            if word[-1] in ("{", "*", "_", "}"):
                word = word[:-1]
                has_changed = True
            else:
                break

    return word if not has_changed else "\\textit{{{}}}".format(word)


def _add_issues(lines, issue, category):
    '''
    :param lines:
        current list to add items

    :param issues:
        List[priority, issue]

    :param str category:
        Category name
    '''

    lines += ["", "", "% ------------------ " + category + "---------------------"]
    lines += ["\\subsection{" + category + "}"]
    
    def getKey(item):
        return int(item[0].id)
    issue.sort(key=getKey)
    
    for issue in issue:
        lines.append(issue[1])


class IssuesToLatex:
    def __init__(self):
        with open('issues_to_latex_config.yaml') as f:
            data = yaml.safe_load(f)

        self._username = data['login']['username']
        self._password = data['login'].get('password')
        self._server = data['login']['server']
        if not self._password:
            self._password = getpass.getpass()

        self._project = data['project_info']['project']
        self._team = data['project_info']['team']
        self._start_date = data['tasks_info']['startdate']
        self._end_date = data['tasks_info']['enddate']

        # resolution types = Fixed, Won't Fix, Done, Won't Do, No longer required by client,
        # Duplicate, Incomplete, cannot reproduce, moved to development
        self._accepted_resolutions = data['tasks_info']['resolutions']

        self._jira = None
        self._custom_fields = {}
        self._issues_to_latex()

    def _issues_to_latex(self):
        options = {'server': 'https://' + self._server}
        basic_auth = (self._username, self._password)
        self._jira = JIRA(basic_auth=basic_auth, options=options, )
        issues = self._search_issues()

        with open('issues_to_latex.txt', 'w', encoding='utf-8') as f:
            solved_issues = []
            unsolved_issues = []
            open_issues = []

            for issue in issues:
                key, resolution_name, summary, description, time_spent, priority, issueType = self._parse_issue(issue)
                if resolution_name is None:
                    report_item = "\\jiraIssue{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}".format(
                        self.safe_latex(key),
                        "Open",
                        self.safe_latex(summary),
                        self.safe_latex(description),
                        self.safe_latex(time_spent),
                        self.safe_latex(str.lower(priority.name)),
                        self.safe_latex(str.lower(issueType))
                    )
                    open_issues.append([priority, report_item])
                    continue
                else:
                    report_item = "\\jiraIssue{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}".format(
                        self.safe_latex(key),
                        self.safe_latex(resolution_name),
                        self.safe_latex(summary),
                        self.safe_latex(description),
                        self.safe_latex(time_spent),
                        self.safe_latex(str.lower(priority.name)),
                        self.safe_latex(str.lower(issueType))
                    )

                if issue.fields.resolution.name not in self._accepted_resolutions:
                    unsolved_issues.append([priority, report_item])
                else:
                    solved_issues.append([priority, report_item])

            lines = []
            _add_issues(lines, solved_issues, "Solved Issues")
            _add_issues(lines, unsolved_issues, "Unsolved Issues")
            _add_issues(lines, open_issues, "Open Issues")

            f.write('\n'.join(lines))

    def _parse_issue(self, issue):
        summary = issue.fields.summary
        description = issue.fields.description if issue.fields.description is not None else None
        resolution_name = issue.fields.resolution.name if issue.fields.resolution is not None else None
        time_spent = format_timespan(issue.fields.timespent) if issue.fields.timespent is not None else None
        priority = issue.fields.priority
        issueType = issue.fields.issuetype.name

        return issue.key, resolution_name, summary, description, time_spent, priority, issueType
    
    def safe_latex(self, text):
        if text is None:
            return ""
        text = str.replace(text, "\\", "\\\\")
        text = str.replace(text, "{", "\\{")
        text = str.replace(text, "}", "\\}")
        text = str.replace(text, "_", "\\textunderscore ")
        text = re.sub(r'(\s*\n\s*)+', '\n', text)
        text = re.sub(r'!(\S+?)!', '', text)
        text = re.sub(r'\n$', '', text)
        text = str.replace(text, "\n", "\\\\")
        return text

    def _search_issues(self):
        team = ", ".join(self._team)
        jql_str = f"project = {self._project} AND status in (Resolved, Closed, Open) AND assignee in ({team}) AND " \
                  f"issuetype in (Bug, Story, Task, Sub-task)  " \
                  f"ORDER BY component ASC, resolved ASC"

        return self._jira.search_issues(jql_str, maxResults=False)


if __name__ == '__main__':
    IssuesToLatex()
