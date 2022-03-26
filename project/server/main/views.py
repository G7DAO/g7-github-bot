from celery.result import AsyncResult
from flask import render_template, Blueprint, jsonify, request
from project.server.tasks import project_task, contributor_task

from .models import TopicData, BuildDatabase

main_blueprint = Blueprint("main", __name__,)


@main_blueprint.route("/", methods=["GET"])
def home():
    return render_template("main/home.html")


@main_blueprint.route("/tasks", methods=["POST"])
def run_task():
    content = request.json
    topic = content["topic"]
    task = project_task.delay(topic)
    return jsonify({"task_id": task.id}), 202


@main_blueprint.route("/contributor-tasks", methods=["POST"])
def run_contributor_task():
    content = request.json
    topic = content["topic"]
    task = contributor_task.delay(topic)
    return jsonify({"task_id": task.id}), 202


@main_blueprint.route("/tasks/<task_id>", methods=["GET"])
def get_status(task_id):
    task_result = AsyncResult(task_id)
    if task_result.result is None:
        result = "..processing"
    else:
        result = task_result.result

    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": result
    }
    return jsonify(result), 200


@main_blueprint.route("/topic/<name>", methods=["GET"])
def get_topic(name):
    # BuildDatabase().process_report()
    total, pages = TopicData(name).get_topic_page_count()
    mes = 'Total Listings Found ' + str(total) + '; Pages ' + str(pages)
    print(mes)
    result = {
        "topic": name,
        "pages": pages,
        "results": total
    }
    return jsonify(result)
