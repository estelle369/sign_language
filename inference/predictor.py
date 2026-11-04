"""
랜덤 포레스트 모델 불러오기와 단어 판정

모델 입력 : (1, 6336)  = (72, 44, 2)를 학습 코드와 같은 순서로 펼친 것
            프레임마다 오른손 0의 x, y, 오른손 1의 x, y ... 순서
모델 출력 : predict_proba 의 (1, 24) 단어별 확률. 라벨 0 ~ 23은 label_map.csv 순서
"""

import csv
import os

import joblib
import numpy as np


MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "rf_noise_model.joblib")
LABEL_MAP_PATH = os.path.join(MODEL_DIR, "label_map.csv")

PROB_THRESHOLD = 0.5  # 확률임계값


def load_model():
    """저장한 랜덤 포레스트 모델을 불러온다."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


def load_label_names():
    """label_map.csv 를 읽어 라벨 번호 순서대로 단어 이름 리스트를 돌려준다. (예: names[17] == "이불")"""
    if not os.path.exists(LABEL_MAP_PATH):
        raise FileNotFoundError(f"라벨 맵 파일을 찾을 수 없습니다: {LABEL_MAP_PATH}")
    names = []
    with open(LABEL_MAP_PATH, "r", encoding="utf-8-sig") as f:  
        reader = csv.DictReader(f)
        for row in reader:
            names.append(row["word"])
    return names


def flatten_sequence(sequence):
    """
    (72, 44, 2)를 모델 입력 (1, 6336)으로 펼친다.
    """
    return sequence.reshape(1, -1).astype(np.float32)


def predict_probabilities(model, sequence):
    """
    구간 하나의 단어별 확률을 구한다.

    sequence : (72, 44, 2) 전처리가 끝난 구간
    반환     : (24,) 단어별 확률. 순서는 label_map.csv 순서
    """
    return model.predict_proba(flatten_sequence(sequence))[0]


def top_words(label_names, probabilities, count=3):
    """확률이 높은 순서로 (단어 이름, 확률) count개를 돌려준다. 로그 출력용."""
    order = np.argsort(probabilities)[::-1][:count]
    return [(label_names[int(i)], float(probabilities[int(i)])) for i in order]


def pick_word(label_names, probabilities):
    """
    단어별 확률에서 최종 단어를 고른다.

    반환 : (단어 이름, 최대 확률). 확률이 PROB_THRESHOLD 미만이면 단어 이름은 None
    """
    best_label = int(np.argmax(probabilities))
    best_prob = float(probabilities[best_label])

    if best_prob < PROB_THRESHOLD:
        return None, best_prob
    return label_names[best_label], best_prob


def predict_word(model, label_names, sequence):
    """
    구간 하나의 단어를 예측한다.

    sequence : (72, 44, 2) 전처리가 끝난 구간
    반환     : (단어 이름, 최대 확률). 확률이 PROB_THRESHOLD 미만이면 단어 이름은 None
    """
    return pick_word(label_names, predict_probabilities(model, sequence))
