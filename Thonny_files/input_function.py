import random

word_list = ["aardvark", "baboon", "camel"]
guess_word = random.choice(word_list)
decoded_word = []
for letter in guess_word:
    decoded_word += "_"

print("Word to guess:", decoded_word)
attempt = 6
while "".join(decoded_word) != guess_word or attempt > 0:
    guess_letter = input("Guess a letter: ")
    correct = False
    for i in range(0, len(guess_word)):
        if guess_letter == guess_word[i]:
            decoded_word[i] = guess_word[i]
            correct = True
    if not correct:
        print("not correct", attempt)
        attempt -= 1
    print("".join(decoded_word))
