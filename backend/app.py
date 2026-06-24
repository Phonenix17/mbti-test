import json
import os
from flask import Flask, jsonify, request, send_from_directory, redirect
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
QUESTIONS_FILE = os.path.join(BASE_DIR, "questions.json")
RESULTS_FILE = os.path.join(BASE_DIR, "results.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

os.makedirs(UPLOAD_DIR, exist_ok=True)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def calculate_mbti(answers):
    """answers: {question_id: selected_score}"""
    scores = {"E": 0, "I": 0, "S": 0, "N": 0, "T": 0, "F": 0, "J": 0, "P": 0}
    questions = load_json(QUESTIONS_FILE)
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


# API: 获取题库
@app.route("/api/questions")
def get_questions():
    questions = load_json(QUESTIONS_FILE)
    return jsonify({"code": 0, "data": questions})


# API: 提交答案
@app.route("/api/submit", methods=["POST"])
def submit():
    data = request.get_json()
    if not data or "answers" not in data:
        return jsonify({"code": 1, "message": "缺少 answers 字段"}), 400

    mbti_type = calculate_mbti(data["answers"])
    results = load_json(RESULTS_FILE)
    type_info = results.get(mbti_type, {"title": "未知", "description": "暂无描述", "traits": [], "suitable": []})

    return jsonify({
        "code": 0,
        "data": {
            "type": mbti_type,
            "info": type_info
        }
    })


# API: 获取结果页配置
@app.route("/api/results")
def get_results():
    results = load_json(RESULTS_FILE)
    return jsonify({"code": 0, "data": results})


# 后台管理页面
@app.route("/admin")
def admin():
    return send_from_directory(os.path.join(BASE_DIR, "templates"), "admin.html")


# API: 上传题库
@app.route("/api/admin/upload-questions", methods=["POST"])
def upload_questions():
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

        # 基本校验
        for item in data:
            if not all(k in item for k in ("id", "dimension", "text", "options")):
                return jsonify({"code": 1, "message": "题目格式不正确，需包含 id/dimension/text/options"}), 400

        # 备份原有题库
        if os.path.exists(QUESTIONS_FILE):
            bak_path = QUESTIONS_FILE + ".bak"
            with open(QUESTIONS_FILE, "r", encoding="utf-8") as f_src:
                with open(bak_path, "w", encoding="utf-8") as f_dst:
                    f_dst.write(f_src.read())

        save_json(QUESTIONS_FILE, data)
        return jsonify({"code": 0, "message": f"题库上传成功，共 {len(data)} 题"})
    except json.JSONDecodeError:
        return jsonify({"code": 1, "message": "JSON 格式解析失败"}), 400
    except Exception as e:
        return jsonify({"code": 1, "message": f"上传失败: {str(e)}"}), 500


# API: 上传结果配置
@app.route("/api/admin/upload-results", methods=["POST"])
def upload_results():
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

        # 备份原有配置
        if os.path.exists(RESULTS_FILE):
            bak_path = RESULTS_FILE + ".bak"
            with open(RESULTS_FILE, "r", encoding="utf-8") as f_src:
                with open(bak_path, "w", encoding="utf-8") as f_dst:
                    f_dst.write(f_src.read())

        save_json(RESULTS_FILE, data)
        return jsonify({"code": 0, "message": f"结果配置上传成功，共 {len(data)} 种类型"})
    except json.JSONDecodeError:
        return jsonify({"code": 1, "message": "JSON 格式解析失败"}), 400
    except Exception as e:
        return jsonify({"code": 1, "message": f"上传失败: {str(e)}"}), 500


# 默认首页 -> 前端测试页
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# PythonAnywhere WSGI 入口
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
