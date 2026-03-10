"""
رَقيب – الراصد الذكي
Flask Backend مع Groq API (مجاني) و Privacy Layer
"""

import os
import json
import requests
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =============================================
# Groq API - مجاني بدون بطاقة بنكية
# احصل على مفتاحك من: console.groq.com
# =============================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Privacy Layer + Groq API (LLM مجاني)
    يستقبل بيانات مجهولة الهوية فقط - بدون اسم أو بيانات شخصية
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400

        edu        = data.get("edu_level", "غير محدد")
        job        = data.get("job_title", "غير محدد")
        birth_year = data.get("birth_year")
        grad_year  = data.get("grad_year")
        salary_rng = data.get("salary_range", "غير محدد")

        prompt = f"""أنت نظام رَقيب لكشف التناقضات الدلالية في بيانات الاستبيانات.
حلّل هذه البيانات المجهولة الهوية بدقة:

- المؤهل الدراسي: {edu}
- المسمى الوظيفي: {job}
- سنة الميلاد: {birth_year or 'غير محددة'}
- سنة التخرج: {grad_year or 'غير محددة'}
- مستوى الراتب: {salary_rng}

تحقق من:
1. هل المؤهل يتناسب مع متطلبات الوظيفة؟
2. هل العمر عند التخرج منطقي؟ (بين 17 و 45 سنة)
3. هل الراتب يتناسب مع المؤهل والوظيفة؟

أجب بـ JSON فقط بدون أي نص خارجه:
{{"has_contradiction": true, "confidence_score": 60, "reason": "سبب واضح بالعربية", "severity": "high"}}

قيم confidence_score: 100 = لا تناقض، أقل = يوجد تناقض
قيم severity: low / medium / high"""

        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type":  "application/json"
            },
            json={
                "model":       GROQ_MODEL,
                "messages":    [{"role": "user", "content": prompt}],
                "max_tokens":  400,
                "temperature": 0.1
            },
            timeout=15
        )

        if response.status_code == 401:
            return jsonify({"error": "GROQ_API_KEY غير صحيح"}), 401
        if response.status_code == 429:
            return jsonify({"error": "تجاوزت حد الطلبات"}), 429

        response.raise_for_status()

        raw = response.json()["choices"][0]["message"]["content"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        result["privacy_confirmed"]  = True
        result["personal_data_sent"] = False

        return jsonify(result)

    except json.JSONDecodeError:
        return jsonify({
            "has_contradiction": False,
            "confidence_score":  80,
            "reason":            "تعذّر تحليل الرد",
            "severity":          "low",
            "privacy_confirmed": True
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":             "ok",
        "api_key_configured": bool(GROQ_API_KEY),
        "model":              GROQ_MODEL,
        "provider":           "Groq - مجاني"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n✅ رَقيب يعمل على: http://localhost:{port}")
    print(f"🔑 Groq Key: {'✅ موجود' if GROQ_API_KEY else '❌ غير موجود'}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
