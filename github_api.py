# -*- coding: utf-8 -*-

import urllib
import urllib2
import datetime as dt
from collections import Counter
import json
import argparse


def get_page_count(repository, api_method, params):
    """
    Функция получает количество страниц для поискового запроса
    """
    # Посылаем запрос с определенными параметрами
    request = urllib2.Request("https://api.github.com/repos/{}/{}?{}".format(
        repository, api_method, urllib.urlencode(params)),
        headers={"Accept": "application/vnd.github.v3.star+json"})
    response = urllib2.urlopen(request)

    # Из headers получаем ссылку на последнюю страницу, парсим номер страницы
    links = response.info().getheader('Link')
    if links:
        links = links.split(", ")
        last = [link for link in links if link.find("last") != -1][0]
        page_count = int(last.split("&page=")[1].split("&")[0].split(">")[0])
        return page_count
    return 1


def get_statistics(client_id, client_secret, api_method, args):
    """
    Функция получает ответ от API по указанному методу и возвращает список значений
    """
    # Парсим аргументы
    repository = args.repository
    branch_name = args.branch_name
    since_date = args.since_date
    until_date = args.until_date
    # Формирование параметров запроса
    params = {"page": 1, "per_page": 100,
              "client_id": client_id, "client_secret": client_secret}
    if api_method != "commits":
        params.update({"state": "all"})
    else:
        if branch_name:
            params.update({'sha': branch_name})
        if since_date:
            params.update({'since': dt.datetime.strptime(
                since_date, "%Y-%m-%d").isoformat(sep='T')})
        if until_date:
            params.update({'until': dt.datetime.strptime(
                until_date, "%Y-%m-%d").isoformat(sep='T')})

    # Получаем количество страниц по запросу
    page_count = get_page_count(repository,
                                api_method,
                                params)

    # Получаем данные из API по каждой странице и формируем список элементов
    api_response = []
    for page in xrange(1, page_count + 1):
        params.update({"page": page})
        request = urllib2.Request("https://api.github.com/repos/{}/{}?{}".format(
            repository, api_method, urllib.urlencode(params)),
            headers={"Accept": "application/vnd.github.v3.star+json"})
        items = json.loads(urllib2.urlopen(request).read())
        for item in items:
            api_response.append(item)

    # Собираем список авторов коммитов для соответствующего метода
    if api_method == "commits":
        api_response = [commit['committer']['login']
                        for commit in api_response if commit['committer']]
    return api_response


def get_user_activity(client_id, client_secret, args):
    """
    Функция используется для подсчета количества коммитов для каждого пользователя, но не более 30 значений
    """
    # Получаем список авторов коммитов
    users = get_statistics(client_id, client_secret, "commits", args)
    # Считаем количество упоминаний автора и сортируем по убыванию значений, но не более 30 авторов
    ordered_dict = Counter(users).most_common(30)
    return ordered_dict


def get_pullrequests(client_id, client_secret, args):
    """
    Функция используется для подсчета количества открытых, закрытых и устаревших pullrequests
    """
    # Получаем все pullrequests
    pulls = get_statistics(client_id, client_secret, "pulls", args)

    # Считаем количество открытых, закрытых, устаревших
    open_requests = sum(
        map(lambda pullrequest: pullrequest['state'] == "open", pulls))
    closed_requests = sum(
        map(lambda pullrequest: pullrequest['state'] == "closed", pulls))
    delay_days = dt.datetime.now() - dt.timedelta(days=30)
    old_requests = sum(map(lambda pullrequest: dt.datetime.strptime(
        pullrequest['created_at'], "%Y-%m-%dT%H:%M:%SZ") < delay_days, pulls))
    return (open_requests, closed_requests, old_requests)


def get_issues(client_id, client_secret, args):
    """
    Функция используется для подсчета количества открытых, закрытых и устаревших issues
    """
    # Получаем все issues
    issues = get_statistics(client_id, client_secret, "issues", args)

    # Считаем количество открытых, закрытых, устаревших
    open_issues = sum(map(lambda issue: issue['state'] == "open", issues))
    closed_issues = sum(map(lambda issue: issue['state'] == "closed", issues))
    delay_days = dt.datetime.now() - dt.timedelta(days=14)
    old_issues = sum(map(lambda issue: dt.datetime.strptime(
        issue['created_at'], "%Y-%m-%dT%H:%M:%SZ") < delay_days, issues))
    return (open_issues, closed_issues, old_issues)


def main():
    client_id = "a4a49f6536b4e90691f3"
    client_secret = "8bf6894591d52eda9f3d694b8b27cabc097e02a3"
    # repository = "jesseduffield/lazygit"
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--repository", dest="repository", type=str, required=True)
    parser.add_argument("-b", "--branch", dest="branch_name", type=str, default="master")
    parser.add_argument("-s", "--start", dest="since_date", type=str, default=None)
    parser.add_argument("-f", "--finish", dest="until_date", type=str, default=None)
    args = parser.parse_args()

    # Вывод статистики по количеству коммитов по пользователям
    for login, count in get_user_activity(client_id, client_secret, args):
        print login, count

    # Вывод статистики по количеству открытх, закрытых и устаревших pullrequests
    print "PullRequests: %d open, %d closed, %d old" % get_pullrequests(client_id, client_secret, args)

    # Вывод статистики по количеству открытх, закрытых и устаревших issues
    print "Issues: %d open, %d closed, %d old" % get_issues(client_id, client_secret, args)


if __name__ == "__main__":
    main()
