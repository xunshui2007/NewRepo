from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# 替换成你的 DeepSeek API Key
DEEPSEEK_API_KEY = "YO8W0K09Po/WutY/2S1fIntmNs/W8Us9F/AngIBgE3k1nnifXWO4xQsZbDS4uMvm"
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"  # 固定
)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message", "")
    if not user_msg:
        return jsonify({"error": "message required"}), 400

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",  # 或 deepseek-reasoner
            messages=[
                {"role": "system", "content": "你是一个有用的助手"},
                {"role": "user", "content": user_msg}
            ],
            stream=False
        )
        return jsonify({
            "reply": resp.choices[0].message.content
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)