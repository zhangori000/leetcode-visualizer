"""Example script for LeetCode 1307: Verbal Addition (alphametic)."""

from __future__ import annotations

from typing import Dict, List, Set

from visualizer.core import RenderSettings, Visualizer


class Solution:
    def isSolvable(self, words: List[str], result: str) -> bool:
        """Return True if there's a digit assignment that satisfies the sum."""

        unique_chars: Set[str] = set("".join(words) + result)
        if len(unique_chars) > 10:
            return False

        leading_chars: Set[str] = {word[0] for word in words if len(word) > 1}
        if len(result) > 1:
            leading_chars.add(result[0])

        reversed_words = [word[::-1] for word in words]
        reversed_result = result[::-1]
        max_word_len = max(len(word) for word in words)
        max_len = max(len(result), max_word_len)

        assignment: Dict[str, int] = {}
        used_digits = [False] * 10

        def solve(column: int, word_index: int, carry: int) -> bool:
            if column == max_len:
                return carry == 0

            if word_index == len(reversed_words):
                total = carry
                for word in reversed_words:
                    if column < len(word):
                        total += assignment[word[column]]

                digit = total % 10
                new_carry = total // 10

                if column < len(reversed_result):
                    res_char = reversed_result[column]
                    assigned_digit = assignment.get(res_char)
                    if assigned_digit is not None:
                        if assigned_digit != digit:
                            return False
                        return solve(column + 1, 0, new_carry)

                    if used_digits[digit]:
                        return False
                    if digit == 0 and res_char in leading_chars:
                        return False

                    assignment[res_char] = digit
                    used_digits[digit] = True
                    try:
                        if solve(column + 1, 0, new_carry):
                            return True
                    finally:
                        used_digits[digit] = False
                        assignment.pop(res_char, None)
                    return False

                return digit == 0 and solve(column + 1, 0, new_carry)

            word = reversed_words[word_index]
            if column >= len(word):
                return solve(column, word_index + 1, carry)

            char = word[column]
            assigned_digit = assignment.get(char)
            if assigned_digit is not None:
                return solve(column, word_index + 1, carry)

            for digit in range(10):
                if used_digits[digit]:
                    continue
                if digit == 0 and char in leading_chars:
                    continue

                assignment[char] = digit
                used_digits[digit] = True
                if solve(column, word_index + 1, carry):
                    return True
                used_digits[digit] = False
                assignment.pop(char, None)

            return False

        return solve(0, 0, 0)


def run_visualization() -> None:
    solver = Solution()
    settings = RenderSettings(
        watch=["column", "word_index", "carry", "assignment", "used_digits"]
    )
    visualizer = Visualizer(settings=settings)
    visualizer.run(solver.isSolvable, ["SEND", "MORE"], "MONEY")


if __name__ == "__main__":
    run_visualization()
