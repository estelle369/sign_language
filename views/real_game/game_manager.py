import random
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class GameManager:


    DEFAULT_WORD_POOL = [
        "발가락", "슬프다", "자극", "영아", "성실", 
        "독서", "면역", "배드민턴", "변비", "불면증", 
        "사위", "찬물", "딸기", "떡국", "막걸리", 
        "부엌", "사이다", "에어컨", "주차장", "채팅", 
        "출근", "디자인", "예술", "참새"
    ]

    def __init__(self, word_pool: Optional[List[str]] = None, target_count: int = 24):
        self.full_word_pool = word_pool if word_pool else self.DEFAULT_WORD_POOL
        self.target_count = min(target_count, len(self.full_word_pool))
        
        self.active_words: List[str] = []
        self.score: int = 0
        self.is_running: bool = False
        
        self.start_new_game()

    def start_new_game(self) -> None:
        """새 게임 시작 (점수 및 단어 리셋)"""
        try:
            self.active_words = random.sample(self.full_word_pool, self.target_count)
            self.score = 0 # 점수 리셋
            self.is_running = True
        except Exception as e:
            self.active_words = []
            self.is_running = False

    def check_answer(self, detected_word: str) -> Dict[str, Any]:
        """정답 판정 및 점수 계산"""
        if not self.is_running:
            return {"is_matched": False, "reason": "게임이 실행 중이 아닙니다."}

        if detected_word in self.active_words:
            self.active_words.remove(detected_word)
            
            # 💡 [점수제 로직] 단어 1개당 +100점 획득
            self.score += 100
            
            is_cleared = self.is_game_cleared()
            if is_cleared:
                self.score += 500 # 올클리어 보너스 점수!
                self.is_running = False
                logging.info(f"🎉 게임 올클리어! 최종 점수: {self.score}점")

            return {
                "is_matched": True,
                "matched_word": detected_word,
                "score": self.score,
                "remaining_count": self.get_remaining_count(),
                "is_cleared": is_cleared
            }

        return {"is_matched": False, "reason": "화면에 없거나 이미 맞힌 단어입니다."}

    def get_remaining_count(self) -> int:
        return len(self.active_words)

    def get_score(self) -> int:
        return self.score

    def is_game_cleared(self) -> bool:
        return len(self.active_words) == 0