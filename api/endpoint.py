import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

# 内存存储（Vercel Serverless 无状态，重启后恢复为 JSON 文件默认值）
_questions_data = None
_results_data = None


def _load_default_questions():
    path = os.path.join(ROOT_DIR, "questions.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_default_results():
    path = os.path.join(ROOT_DIR, "results.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_questions():
    global _questions_data
    if _questions_data is None:
        _questions_data = _load_default_questions()
    return _questions_data


def get_results():
    global _results_data
    if _results_data is None:
        _results_data = _load_default_results()
    return _results_data


def calculate_mbti(answers):
    scores = {"E": 0, "I": 0, "S": 0, "N": 0, "T": 0, "F": 0, "J": 0, "P": 0}
    questions = get_questions()
    question_map = {q["id"]: q for q in questions}

    for qid_str, score in answers.items():
        qid = int(qid_str)
        if qid in question_map:
            scores[score] += 1

    result = ""
    result += "E" if scores["E"] >= scores["I"] else "I"
    result += "S" if scores["S"] >= scores["N"] else "N"
    result += "T" if scores["T"] >= scores["F"] else "F"
    result += "J" if scores["J"] >= scores["P"] else "P"
    return result


app = Flask(__name__)
CORS(app)


# GET /api/questions
@app.route("/api/questions")
def api_questions():
    return jsonify({"code": 0, "data": get_questions()})


# POST /api/submit
@app.route("/api/submit", methods=["POST"])
def api_submit():
    data = request.get_json()
    if not data or "answers" not in data:
        return jsonify({"code": 1, "message": "缺少 answers 字段"}), 400

    mbti_type = calculate_mbti(data["answers"])
    results = get_results()
    type_info = results.get(mbti_type, {
        "title": "未知",
        "description": "暂无描述",
        "traits": [],
        "suitable": []
    })

    return jsonify({
        "code": 0,
        "data": {
            "type": mbti_type,
            "info": type_info
        }
    })


# GET /api/results
@app.route("/api/results")
def api_results():
    return jsonify({"code": 0, "data": get_results()})


# POST /api/admin/upload-questions
@app.route("/api/admin/upload-questions", methods=["POST"])
def api_upload_questions():
    global _questions_data

    # 支持 JSON body 方式（管理后台直接编辑 JSON 文本）
    data = request.get_json(silent=True)
    if data is not None:
        if not isinstance(data, list):
            return jsonify({"code": 1, "message": "题库必须是 JSON 数组"}), 400
        for item in data:
            if not all(k in item for k in ("id", "dimension", "text", "options")):
                return jsonify({"code": 1, "message": "题目格式不正确，需包含 id/dimension/text/options"}), 400
        _questions_data = data
        return jsonify({"code": 0, "message": f"题库更新成功，共 {len(data)} 题"})

    # 支持文件上传方式
    if "file" not in request.files:
        return jsonify({"code": 1, "message": "未选择文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"code": 1, "message": "未选择文件"}), 400

    if not file.filename.endswith(".json"):
        return jsonify({"code": 1, "message": "仅支持 JSON 格式"}), 400

    try:
        content = file.read().decode("utf-8")
        data = json.loads(content)
        if not isinstance(data, list):
            return jsonify({"code": 1, "message": "题库必须是 JSON 数组"}), 400
        for item in data:
            if not all(k in item for k in ("id", "dimension", "text", "options")):
                return jsonify({"code": 1, "message": "题目格式不正确，需包含 id/dimension/text/options"}), 400

        _questions_data = data
        return jsonify({"code": 0, "message": f"题库上传成功，共 {len(data)} 题"})
    except json.JSONDecodeError:
        return jsonify({"code": 1, "message": "JSON 格式解析失败"}), 400


# POST /api/admin/upload-results
@app.route("/api/admin/upload-results", methods=["POST"])
def api_upload_results():
    global _results_data

    # 支持 JSON body 方式
    data = request.get_json(silent=True)
    if data is not None:
        if not isinstance(data, dict):
            return jsonify({"code": 1, "message": "结果配置必须是 JSON 对象"}), 400
        _results_data = data
        return jsonify({"code": 0, "message": f"结果配置更新成功，共 {len(data)} 种类型"})

    # 支持文件上传方式
    if "file" not in request.files:
        return jsonify({"code": 1, "message": "未选择文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"code": 1, "message": "未选择文件"}), 400

    if not file.filename.endswith(".json"):
        return jsonify({"code": 1, "message": "仅支持 JSON 格式"}), 400

    try:
        content = file.read().decode("utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            return jsonify({"code": 1, "message": "结果配置必须是 JSON 对象"}), 400

        _results_data = data
        return jsonify({"code": 0, "message": f"结果配置上传成功，共 {len(data)} 种类型"})
    except json.JSONDecodeError:
        return jsonify({"code": 1, "message": "JSON 格式解析失败"}), 400


# GET /api/admin - 返回管理后台状态信息
@app.route("/api/admin")
def api_admin_info():
    questions = get_questions()
    results = get_results()
    return jsonify({
        "code": 0,
        "data": {
            "question_count": len(questions),
            "result_count": len(results),
            "versions": {
                "questions": "memory" if _questions_data is not None else "default",
                "results": "memory" if _results_data is not None else "default"
            }
        }
    })


# Vercel Serverless 入口
app = app
