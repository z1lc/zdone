from typing import List

import ebisu

model = ebisu.defaultModel(t=2)

review_intervals: List[int] = []

i = 0
j = 0
while len(review_intervals) < 20:
    j += 1
    probability = ebisu.predictRecall(model, i, exact=True)
    if j == 50:
        model = ebisu.updateRecall(model, 0, 1, i)
    if probability < 0.5:
        review_intervals += [i]
        print(model)
        model = ebisu.updateRecall(model, 1, 1, i)
        i = 0
    else:
        i += 1

print(review_intervals)
