# coding: utf8

import datetime
from optparse import OptionParser

import gitlab

from config import GITLAB_HOST
from utils import simplecache


BRANCH_NAME_MAP = {
    "feature": u"新功能",
    "fix": u"bug",
    "refactor": u"重构"
}


class Gitlab(gitlab.Gitlab):
    def __init__(self, token):
        super(Gitlab, self).__init__(GITLAB_HOST, token=token)
        user = self.currentuser()
        self.user = user["name"]
        self.email = user["email"]

    def _format_datetime(self, time):
        return datetime.datetime.strptime(
            time.split("T", 1)[0], "%Y-%m-%d"
        )

    @simplecache
    def getprojects(self):
        return super(Gitlab, self).getprojects()

    @simplecache
    def listrepositorycommit(self, project_id, sha1):
        return super(Gitlab, self).listrepositorycommit(project_id, sha1)

    @simplecache
    def listbranches(self, project_id):
        return super(Gitlab, self).listbranches(project_id)

    @simplecache
    def getprojectissues(self, project_id):
        return super(Gitlab, self).getprojectissues(project_id)

    @simplecache
    def getissuewallnotes(self, project_id, issue_id):
        return super(Gitlab, self).getissuewallnotes(project_id, issue_id)

    @simplecache
    def getmergerequests(self, project_id):
        return super(Gitlab, self).getmergerequests(project_id)

    @simplecache
    def getmergerequestwallnotes(self, project_id, mr_id):
        return super(Gitlab, self).getmergerequestwallnotes(project_id, mr_id)

    def _get_all_commits(self, project_id, sha1, user, email, date):
        commit = self.listrepositorycommit(project_id, sha1)
        if self._format_datetime(commit["committed_date"]) < date:
            return
        if commit["author_email"] == email or commit["author_name"] == user:
            yield commit
        parents = commit["parent_ids"]
        if len(parents) == 1:
            self._get_all_commits(
                project_id, parents[0], user, email, date
            )

    def _has_notes(self, notes, user, email, date):
        for note in sorted(
            notes, key=lambda x: x["created_at"], reverse=True
        ):
            if self._format_datetime(note["created_at"]) < date and (
                note["author"]["name"] == user or note["author"]["email"] == email
            ):
                return True
        return False

    def codes(self, project_id, user, email, date):
        res = dict()
        branches = self.listbranches(project_id)
        for branch in branches:
            auth = branch["commit"]["author"]["name"]
            auth_email = branch["commit"]["author"]["email"]
            committed_date = self._format_datetime(
                branch["commit"]["committed_date"]
            )
            if (auth == user or auth_email == email) and committed_date >= date:
                branch_name = branch["name"]
                commit_id = branch["commit"]["id"]
                res[branch_name] = []
                for commit in self._get_all_commits(
                    project_id, commit_id, user, email, date
                ):
                    res[branch_name].append(commit)
        return res

    def issues(self, project_id, user, email, date):
        res = dict()
        issues = self.getprojectissues(project_id)
        for issue in sorted(
            issues, key=lambda x: x["updated_at"], reverse=True
        ):
            if self._format_datetime(issue["created_at"]) >= date:
                if issue["author"]["name"] == user or issue["author"]["email"] == email:
                    if "create" not in res:
                        res["create"] = []
                    res["create"].append(issue)
            elif self._format_datetime(issue["updated_at"]) >= date:
                if issue["author"]["name"] == user or issue["author"]["email"] == email:
                    if "update" not in res:
                        res["update"] = []
                    res["update"].append(issue)
            notes = self.getissuewallnotes(project_id, issue["id"])
            if self._has_notes(notes, user, email, date):
                if "note" not in res:
                    res["note"] = []
                res["note"].append(issue)
        return res

    def merge_requests(self, project_id, user, email, date):
        res = dict()
        mrs = self.getmergerequests(project_id)
        for mr in sorted(
            mrs, key=lambda x: x["created_at"], reverse=True
        ):
            if (mr["author"]["name"] == user or mr["author"]["email"] == email) and \
                    self._format_datetime(mr["created_at"]) >= date:
                if "merget" not in res:
                    res["merge"] = []
                res["merge"].append(mr)
            # TODO: need gather the accept time and the operator
            notes = self.getmergerequestwallnotes(project_id, mr["id"])
            if self._has_notes(notes, user, email, date):
                if "note" not in res:
                    res["note"] = []
                res["note"].append(mr)
        return res

    def get_contribute_details(self, user, email, date):
        """
        return:
        """
        projects = self.getprojects()
        res = dict()
        for project in projects:
            project_name = project["name"]
            project_id = project["id"]
            if project_name not in res:
                res[project_name] = dict(
                    codes={}, issues={}, merge_requests={}
                )

            for label in ("codes", "issues", "merge_requests"):
                contributes = getattr(self, label)(project_id, user, email, date)
                if contributes:
                    res[project_name][label].update(contributes)
        return res

    def get_my_contributes(self, date):
        return self.get_contribute_details(self.user, self.email, date)


class Stat(object):
    def __init__(self, git):
        self.git = git

    def _today(self):
        now = datetime.datetime.now()
        return datetime.datetime(now.year, now.month, now.day)

    def stat_my_daily(self):
        res = self.git.get_my_contributes(self._today())

        text = u"本日工作:\n\n"
        text += self._stat(res)
        return text

    def stat_my_weekly(self):
        res = self.git.get_my_contributes(
            self._today() - datetime.timedelta(days=7)
        )

        text = u"本周工作:\n\n"
        text += self._stat(res)
        return text

    def _stat(self, res):
        text = u""
        for project, labels in res.iteritems():
            if not any(labels.values()):
                continue
            index = 1
            text += project + u":\n"
            codes = labels["codes"]
            for branch in codes:
                try:
                    key, name = branch.split("/", 1)
                except:
                    key = u"feature"
                    name = branch
                text += u"%d. 关于%s的推进\n" % (
                    index, u"%s %s" % (BRANCH_NAME_MAP.get(key, ""),
                                       name.replace("_", " "))
                )
                index += 1
            issues = labels["issues"]
            for key, values in issues.iteritems():
                if key == "create":
                    text += u"%d. 发现并提出了问题(%s)准备解决\n" % (
                        index, ",".join([issue.get("title") for issue in values])
                    )
                    index += 1
                elif key == "update":
                    text += u"%d. 更新了问题(%s)\n" % (
                        index, u",".join([issue.get("title") for issue in values])
                    )
                    index += 1
                elif key == "note":
                    text += u"%d. 跟进了(%s)\n" % (
                        index, u",".join([issue.get("title") for issue in values])
                    )
                    index += 1
            mrs = labels["merge_requests"]
            for key, values in mrs.iteritems():
                if key == "merge":
                    for mr in values:
                        try:
                            key, name = mr["title"].split("/", 1)
                        except:
                            key = "feature"
                            name = mr["title"]
                        text += u"%d. 完成%s并提交准备上线\n" % (
                            index, u"%s %s" % (BRANCH_NAME_MAP.get(key, ""),
                                               name.replace("_", " "))
                        )
                if key == "note":
                    branches = []
                    for mr in values:
                        try:
                            key, name = mr["title"].split("/", 1)
                        except:
                            key = "feature"
                            name = mr["title"]
                    branches.append(u"%s %s" % (key, name))
                    text += u"%d. 跟进(%s)的review\n" % (
                        index, u",".join(branches)
                    )
        return text


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option(
        "-t", "--stat_type",
        default="daily",
        help="stat type.can choose daily/weekly"
    )
    opts, args = parser.parse_args()
    print opts, args
    if len(args) >= 1:
        stat = Stat(Gitlab(args[0]))
        stat_type = opts.stat_type
        if stat_type == "daily":
            print stat.stat_my_daily().encode("utf8", "ignore")
        elif stat_type == "weekly":
            print stat.stat_my_weekly().encode("utf8", "ignore")
