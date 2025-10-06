from collections import Counter
import math

from visualizer.core import RenderSettings, Visualizer


class Solution:
    def countGoodSubsequences(self, s: str) -> int:
        counts = Counter(s)
        unique_letters = list(counts.keys())
        ans = 0
        mod = 10 ** 9 + 7
        for bit_mask in range(1, 2 ** (len(unique_letters))):
            current = bit_mask
            current_letter_set = []
            smallest_freq = float("inf")
            for i in range(32):
                if (current >> i) & 1:
                    current_letter_set.append(unique_letters[i])
                    smallest_freq = min(smallest_freq, counts[unique_letters[i]])
            if len(current_letter_set) == 1:
                ans += (2 ** (counts[current_letter_set[0]]) - 1) % mod
            else:
                for k in range(1, int(smallest_freq) + 1):
                    result = 1
                    for letter in current_letter_set:
                        if counts[letter] >= k:
                            ways = math.comb(counts[letter], k)
                            result *= (ways % mod)
                    ans += (result % mod)
        return ans % mod


def run_visualization():
    solver = Solution()
    settings = RenderSettings(watch=["ans", "current_letter_set", "bit_mask", "result"])
    visualizer = Visualizer(settings=settings)
    visualizer.run(solver.countGoodSubsequences, "aabc")


if __name__ == "__main__":
    run_visualization()
