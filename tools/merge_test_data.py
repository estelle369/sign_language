"""
수집한 테스트 데이터를 단어별 파일로 합치고, 모델 평가용 배열로 저장한다

입력: collect_test_data.py 결과 (동작 하나마다 pkl 하나)
    collected_data/samples/WORD0008/TEST01_1.pkl, TEST01_2.pkl, TEST02_1.pkl ...
    여러 컴퓨터에서 모았다면 samples/ 폴더를 하나로 합친 뒤 실행한다 (파일 이름이 겹치지 않는다)

출력: collected_data/WORD<word_id 4자리>_72.pkl  (label_map.csv 의 24단어, 단어별 1개)
    {"word": "발가락",
     "subjects": {"TEST01_1": {"person": 1, "rep": 1, "sequence": ndarray(72, 44, 2)}, ...}}

    collected_data/dataset/  (build_dataset.py 출력과 같은 형식, 이름만 _test)
        x_test.npy        (샘플 수, 72, 44, 2)  float32 — 모델 입력
        y_test.npy        (샘플 수,)            int64   — 정답(라벨) 0~23, label_map.csv 순서
        person_test.npy   (샘플 수,)            int64   — 사람 번호 (TEST01 -> 1)

build_dataset.py 와 다른 점
    한 사람이 같은 단어를 여러 번 하므로 subjects 키가 "사람_반복번호"(TEST01_1)이다.
    사람 번호는 키를 잘라 쓰지 말고(int(key[4:]) 는 "01_1" 에서 오류) subjects[key]["person"] 을 쓴다.

실행 (프로젝트 폴더에서)
    .venv/bin/python tools/merge_test_data.py
"""

import os
import pickle
import sys

import numpy as np

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, "tools"))

from collect_test_data import SAMPLE_DIR, load_label_map   # noqa: E402

OUTPUT_DIR = os.path.join(PROJECT_DIR, "collected_data")
DATASET_DIR = os.path.join(OUTPUT_DIR, "dataset")

SEQ_LEN = 72
NUM_POINTS = 44


def main():
    label_map = load_label_map()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    x_list = []
    y_list = []
    person_list = []

    for label in range(len(label_map)):
        word_id, word = label_map[label]
        word_dir = os.path.join(SAMPLE_DIR, "WORD%04d" % word_id)

        subjects = {}
        file_names = sorted(os.listdir(word_dir)) if os.path.isdir(word_dir) else []
        for file_name in file_names:
            if not file_name.endswith(".pkl"):
                continue
            with open(os.path.join(word_dir, file_name), "rb") as f:
                sample = pickle.load(f)

            # 형태와 값 검사 (build_dataset.py 와 같은 기준)
            sequence = sample["sequence"]
            if sample["word_id"] != word_id:
                raise ValueError("%s: word_id %d 가 폴더(WORD%04d)와 다르다" % (file_name, sample["word_id"], word_id))
            if sequence.shape != (SEQ_LEN, NUM_POINTS, 2):
                raise ValueError("WORD%04d %s: shape %s" % (word_id, file_name, str(sequence.shape)))
            if np.isnan(sequence).any():
                raise ValueError("WORD%04d %s: NaN 포함" % (word_id, file_name))

            subject_key = file_name[:-len(".pkl")]   # "TEST01_1"
            subjects[subject_key] = {
                "person": sample["person"],
                "rep": sample["rep"],
                "sequence": sequence,
            }
            x_list.append(sequence)
            y_list.append(label)
            person_list.append(sample["person"])

        with open(os.path.join(OUTPUT_DIR, "WORD%04d_72.pkl" % word_id), "wb") as f:
            pickle.dump({"word": word, "subjects": subjects}, f)

        persons = sorted(set(s["person"] for s in subjects.values()))
        print("라벨 %2d  WORD%04d  %-6s  %2d개 (사람 %s)" % (label, word_id, word, len(subjects), persons))

    print()
    print("전체 %d개 → %s/WORD____72.pkl 24개" % (len(x_list), OUTPUT_DIR))
    if not x_list:
        print("수집된 샘플이 없어 x_test.npy 는 만들지 않습니다.")
        return

    X = np.stack(x_list).astype(np.float32)             # (샘플 수, 72, 44, 2)
    y = np.array(y_list, dtype=np.int64)                # (샘플 수,)
    person = np.array(person_list, dtype=np.int64)      # (샘플 수,)

    os.makedirs(DATASET_DIR, exist_ok=True)
    np.save(os.path.join(DATASET_DIR, "x_test.npy"), X)
    np.save(os.path.join(DATASET_DIR, "y_test.npy"), y)
    np.save(os.path.join(DATASET_DIR, "person_test.npy"), person)

    print("X:", X.shape, " y:", y.shape, " person:", person.shape, "→", DATASET_DIR)
    print("사람 번호:", sorted(set(person_list)), "(%d명)" % len(set(person_list)))


if __name__ == "__main__":
    main()
