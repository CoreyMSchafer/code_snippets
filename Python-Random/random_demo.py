import random

deck = list(range(1, 53))

hand = random.sample(deck, k=5)
print(hand)
