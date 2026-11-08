"""
테스트 데이터 수집 (게임과 같은 파이프라인)

    카운트다운 5초 → 캘리브레이션 → 손목 트리거로 동작 구간 자르기 → 전처리 → (72, 44, 2) 저장

    - 한 번 실행에 단어 하나(--word)만 --reps 번 수집하고 끝난다.
      예시 영상을 보고 동작을 익힌 뒤 단어마다 다시 실행한다

    - 웹캠 원본 프레임은 저장하지도 화면에 보여주지도 않는다. 화면과 영상에는 Mediapipe 키포인트(손, 팔꿈치, 어깨)만 그린다
    - 구간 안에서 한 부위라도 연속 결측이 기준(MAX_MISSING_RUN 5프레임)을 넘으면 게임처럼 인식하지 않는 구간이다.
      화면을 빨간색으로 바꾸고 카운트다운부터 다시 한다
    - 파일 이름에는 label_map.csv 의 word_id 를 쓴다.
      화면에는 한글이 나오지 않으므로 word_id 로 보여주고, 한글 단어 이름은 터미널에 출력한다

실행 (프로젝트 폴더에서, --person 은 사람 번호, --word 는 label_map.csv 의 word_id)
    .venv/bin/python tools/collect_test_data.py --person 1 --word 0008 --reps 3

    q 키: 종료. 같은 단어로 다시 실행하면 이미 저장된 동작은 건너뛰고 이어서 수집한다

저장 (동작 하나마다 한 쌍. 사람마다 파일이 따로라 다른 컴퓨터에서 모은 폴더를 그대로 합칠 수 있다)
    collected_data/samples/WORD<word_id 4자리>/TEST<사람 2자리>_<반복 번호>.pkl
        {"word_id": int, "word": str, "person": int, "rep": int, "num_frames": int,
         "sequence": (72, 44, 2) float32}
    collected_data/samples/WORD<word_id 4자리>/TEST<사람 2자리>_<반복 번호>.mp4
        잘라낸 구간 프레임의 키포인트 영상 (pkl 을 만든 프레임과 같다. 좌우 반전하지 않음)
    잘못된 동작은 pkl 과 mp4 를 같이 지우고 다시 실행하면 그 동작만 다시 수집한다

    모은 뒤 tools/merge_test_data.py 로 단어별 WORD<word_id 4자리>_72.pkl 24개를 만든다 (build_dataset.py 입력 형식)
"""

import argparse
import csv
import os
import pickle
import sys
import time

import cv2
import numpy as np

# tools/ 에서 실행해도 inference 패키지를 찾을 수 있게 프로젝트 폴더를 경로에 넣는다
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from inference import mediapipe_extractor, predictor, preprocessor   # noqa: E402
from inference.camera import CameraStream                             # noqa: E402
from inference.trigger import SegmentTrigger                          # noqa: E402

SAMPLE_DIR = os.path.join(PROJECT_DIR, "collected_data", "samples")
PERSON_PREFIX = "TEST"   # 학습 데이터(REAL01 ~)와 구분한다

CAMERA_INDEX = 0
CAMERA_READ_TIMEOUT_SECONDS = 3.0
COUNTDOWN_SECONDS = 5
RESULT_SHOW_SECONDS = 1.5   # 저장 완료(초록) / 결측(빨강) 화면을 보여주는 시간
VIDEO_FPS = 30              # 실제 처리 속도는 약 28 ~ 29fps (근사값)
WINDOW_NAME = "collect"

# 화면 상태
STATE_COUNTDOWN = "countdown"     # 5, 4, 3, 2, 1
STATE_CALIBRATE = "calibrate"     # 쉬는 높이를 잴 때까지 (Pose가 잡힌 첫 프레임)
STATE_SIGNING = "signing"         # 동작 구간을 기다리는 중
STATE_SAVED = "saved"             # 저장 완료 표시
STATE_MISSING = "missing"         # 결측으로 다시 하기 표시

# 손 21점 연결선 (MediaPipe 손 모델 기준)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),           # 엄지
    (0, 5), (5, 6), (6, 7), (7, 8),           # 검지
    (5, 9), (9, 10), (10, 11), (11, 12),      # 중지
    (9, 13), (13, 14), (14, 15), (15, 16),    # 약지
    (13, 17), (17, 18), (18, 19), (19, 20),   # 새끼
    (0, 17),
]
RIGHT_ELBOW, LEFT_ELBOW, RIGHT_SHOULDER, LEFT_SHOULDER = 42, 43, 44, 45

COLOR_RIGHT_HAND = (0, 200, 255)   # BGR 주황
COLOR_LEFT_HAND = (255, 200, 0)    # BGR 하늘
COLOR_POSE = (200, 200, 200)       # 회색
COLOR_TEXT = (255, 255, 255)


def draw_keypoints(canvas, xy, right_missing, left_missing, pose_missing):
    """검은 화면(canvas)에 손·팔꿈치·어깨 키포인트를 그린다. 검출되지 않은 부위는 그리지 않는다."""
    def point(i):
        return int(xy[i, 0]), int(xy[i, 1])

    if not pose_missing:
        cv2.line(canvas, point(RIGHT_SHOULDER), point(LEFT_SHOULDER), COLOR_POSE, 2)
        cv2.line(canvas, point(RIGHT_SHOULDER), point(RIGHT_ELBOW), COLOR_POSE, 2)
        cv2.line(canvas, point(LEFT_SHOULDER), point(LEFT_ELBOW), COLOR_POSE, 2)
        # 팔꿈치 → 손목 (손이 검출된 경우만. 손목 = 손 0번 점)
        if not right_missing:
            cv2.line(canvas, point(RIGHT_ELBOW), point(preprocessor.RIGHT_HAND_START), COLOR_POSE, 2)
        if not left_missing:
            cv2.line(canvas, point(LEFT_ELBOW), point(preprocessor.LEFT_HAND_START), COLOR_POSE, 2)
        for i in (RIGHT_ELBOW, LEFT_ELBOW, RIGHT_SHOULDER, LEFT_SHOULDER):
            cv2.circle(canvas, point(i), 6, COLOR_POSE, -1)

    hands = [
        (preprocessor.RIGHT_HAND_START, right_missing, COLOR_RIGHT_HAND),
        (preprocessor.LEFT_HAND_START, left_missing, COLOR_LEFT_HAND),
    ]
    for start, missing, color in hands:
        if missing:
            continue
        for a, b in HAND_CONNECTIONS:
            cv2.line(canvas, point(start + a), point(start + b), color, 2)
        for p in range(mediapipe_extractor.HAND_POINT_COUNT):
            cv2.circle(canvas, point(start + p), 3, color, -1)


def draw_text(canvas, text, y, scale=1.0, thickness=2):
    cv2.putText(canvas, text, (20, y), cv2.FONT_HERSHEY_SIMPLEX, scale, COLOR_TEXT, thickness, cv2.LINE_AA)


def draw_center_text(canvas, text, scale=4.0, thickness=8):
    height, width = canvas.shape[:2]
    (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    position = ((width - text_w) // 2, (height + text_h) // 2)
    cv2.putText(canvas, text, position, cv2.FONT_HERSHEY_SIMPLEX, scale, COLOR_TEXT, thickness, cv2.LINE_AA)


def load_label_map():
    """label_map.csv 를 label 순서대로 읽는다. 반환: [(word_id, 단어 이름), ...] (리스트 번호 = label)"""
    rows = []
    with open(predictor.LABEL_MAP_PATH, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append((int(row["word_id"]), row["word"]))
    return rows


def sample_path(word_id, person, rep, extension):
    """예: collected_data/samples/WORD0008/TEST01_2.pkl"""
    return os.path.join(SAMPLE_DIR, "WORD%04d" % word_id, "%s%02d_%d.%s" % (PERSON_PREFIX, person, rep, extension))


def save_sample(word_id, word, person, rep, sequence, segment, frame_size):
    """전처리 결과를 pkl 로, 잘라낸 구간의 키포인트 영상을 mp4 로 저장한다."""
    os.makedirs(os.path.dirname(sample_path(word_id, person, rep, "pkl")), exist_ok=True)
    data = {
        "word_id": word_id,
        "word": word,
        "person": person,
        "rep": rep,
        "num_frames": len(segment[0]),             # 리샘플링 전 구간 길이 (확인용)
        "sequence": sequence.astype(np.float32),   # (72, 44, 2)
    }
    with open(sample_path(word_id, person, rep, "pkl"), "wb") as f:
        pickle.dump(data, f)

    seg_xy, seg_right_missing, seg_left_missing, seg_pose_missing = segment
    width, height = frame_size
    writer = cv2.VideoWriter(sample_path(word_id, person, rep, "mp4"),
                             cv2.VideoWriter_fourcc(*"mp4v"), VIDEO_FPS, (width, height))
    for t in range(len(seg_xy)):
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        draw_keypoints(canvas, seg_xy[t], seg_right_missing[t], seg_left_missing[t], seg_pose_missing[t])
        writer.write(canvas)
    writer.release()


def missing_report(segment):
    """결측으로 인식하지 않은 구간의 부위별 최장 연속 결측 프레임 수 (터미널 출력용)."""
    _, right_missing, left_missing, pose_missing = segment
    return (f"최장 연속 결측: 오른손 {preprocessor.longest_missing_run(right_missing)}, "
            f"왼손 {preprocessor.longest_missing_run(left_missing)}, "
            f"Pose {preprocessor.longest_missing_run(pose_missing)} "
            f"(기준: {preprocessor.MAX_MISSING_RUN} 초과면 제외)")


def build_jobs(label, word_id, person, reps):
    """수집할 (label, 반복 번호 1 ~ reps) 목록. 이미 저장된 동작은 뺀다."""
    jobs = []
    for rep in range(1, reps + 1):
        if not os.path.exists(sample_path(word_id, person, rep, "pkl")):
            jobs.append((label, rep))
    return jobs


def main():
    parser = argparse.ArgumentParser(description="게임과 같은 파이프라인으로 테스트 데이터를 수집한다")
    parser.add_argument("--person", type=int, required=True, help="사람 번호 (1, 2, 3 ...). TEST01 처럼 저장된다")
    parser.add_argument("--word", type=int, required=True,
                        help="수집할 단어의 word_id (label_map.csv). 0008 처럼 써도 된다")
    parser.add_argument("--reps", type=int, default=3, help="단어마다 수집할 동작 수 (기본 3)")
    args = parser.parse_args()

    label_map = load_label_map()
    person_name = "%s%02d" % (PERSON_PREFIX, args.person)

    word_ids = [word_id for word_id, _ in label_map]
    if args.word not in word_ids:
        print(f"word_id {args.word} 는 label_map.csv 에 없습니다. 아래 번호 중 하나를 쓰세요.")
        for label, (word_id, word) in enumerate(label_map):
            print(f"  WORD{word_id:04d}  {word}")
        return
    target_label = word_ids.index(args.word)

    jobs = build_jobs(target_label, args.word, args.person, args.reps)
    if not jobs:
        print(f"{person_name}: WORD{args.word:04d} {label_map[target_label][1]} 를 {args.reps}번 모두 수집했습니다.")
        return
    print(f"{person_name} WORD{args.word:04d} {label_map[target_label][1]} 남은 수집: {len(jobs)}번 / 저장 위치: {SAMPLE_DIR}")

    hand_landmarker, pose_landmarker = mediapipe_extractor.create_landmarkers()
    camera = CameraStream(CAMERA_INDEX)
    camera.start()

    job_index = 0
    state = None
    state_start = 0.0
    trigger = None
    last_id = -1

    def begin_job():
        """현재 동작의 카운트다운을 시작한다 (처음, 저장 후, 결측으로 다시 할 때)."""
        nonlocal state, state_start, trigger
        label, rep = jobs[job_index]
        word_id, word = label_map[label]
        print(f"\n[{job_index + 1}/{len(jobs)}] WORD{word_id:04d} {word} ({rep}/{args.reps}번째)")
        state = STATE_COUNTDOWN
        state_start = time.time()
        trigger = SegmentTrigger()

    def change_state(new_state):
        nonlocal state, state_start
        state = new_state
        state_start = time.time()

    begin_job()
    try:
        while True:
            frame, last_id, timestamp_ms = camera.read(last_id, CAMERA_READ_TIMEOUT_SECONDS)
            if frame is None:
                print("카메라에서 프레임을 받지 못했습니다.", file=sys.stderr)
                break
            height, width = frame.shape[:2]

            # 모든 상태에서 MediaPipe 에 계속 넣는다 (VIDEO 모드 추적이 이어지도록)
            xy, right_missing, left_missing, pose_missing, wrist_xy = mediapipe_extractor.extract_keypoints(
                hand_landmarker, pose_landmarker, frame, timestamp_ms)
            del frame   # 원본 프레임은 쓰지 않는다

            elapsed = time.time() - state_start
            label, rep = jobs[job_index]
            word_id, word = label_map[label]

            if state == STATE_COUNTDOWN and elapsed >= COUNTDOWN_SECONDS:
                change_state(STATE_CALIBRATE)

            if state == STATE_CALIBRATE:
                if trigger.calibrate(xy, pose_missing, wrist_xy):
                    change_state(STATE_SIGNING)
            elif state == STATE_SIGNING:
                segment = trigger.process_frame(xy, right_missing, left_missing, pose_missing, wrist_xy)
                if segment is not None:
                    frame_numbers = np.arange(len(segment[0]), dtype=np.float64)   # 게임과 같은 시간축
                    sequence = preprocessor.preprocess_segment(frame_numbers, *segment)
                    if sequence is None:
                        print(f"  결측으로 다시 합니다 (구간 {len(segment[0])}프레임) | {missing_report(segment)}")
                        change_state(STATE_MISSING)
                    else:
                        save_sample(word_id, word, args.person, rep, sequence, segment, (width, height))
                        print(f"  저장: {sample_path(word_id, args.person, rep, 'pkl')} (구간 {len(segment[0])}프레임)")
                        change_state(STATE_SAVED)
            elif state == STATE_MISSING and elapsed >= RESULT_SHOW_SECONDS:
                begin_job()   # 같은 동작을 카운트다운부터 다시
            elif state == STATE_SAVED and elapsed >= RESULT_SHOW_SECONDS:
                job_index += 1
                if job_index >= len(jobs):
                    print("\n수집을 모두 마쳤습니다.")
                    break
                begin_job()

            # 화면: 키포인트만 그린 뒤 거울처럼 좌우 반전해서 보여준다 (저장 데이터와 영상은 반전하지 않음)
            label, rep = jobs[job_index]
            word_id = label_map[label][0]
            canvas = np.zeros((height, width, 3), dtype=np.uint8)
            if state == STATE_MISSING:
                canvas[:] = (0, 0, 200)     # 빨강 (BGR)
            elif state == STATE_SAVED:
                canvas[:] = (0, 140, 0)     # 초록
            draw_keypoints(canvas, xy, right_missing, left_missing, pose_missing)
            canvas = cv2.flip(canvas, 1)

            draw_text(canvas, f"{person_name}  WORD {word_id:04d}  ({rep}/{args.reps})", 40)
            draw_text(canvas, f"total {job_index + 1}/{len(jobs)}   q: quit", 75, scale=0.7)
            if state == STATE_COUNTDOWN:
                draw_center_text(canvas, str(COUNTDOWN_SECONDS - int(elapsed)))
            elif state == STATE_CALIBRATE:
                draw_center_text(canvas, "STAND STILL", scale=1.5, thickness=4)
            elif state == STATE_SIGNING:
                draw_text(canvas, "SIGN NOW", height - 30, scale=1.2, thickness=3)
            elif state == STATE_MISSING:
                draw_center_text(canvas, "MISSING - RETRY", scale=1.5, thickness=4)
            elif state == STATE_SAVED:
                draw_center_text(canvas, "SAVED", scale=2.0, thickness=5)

            cv2.imshow(WINDOW_NAME, canvas)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("\n중간에 종료했습니다. 다시 실행하면 이어서 수집합니다.")
                break
    finally:
        camera.stop()
        hand_landmarker.close()
        pose_landmarker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
