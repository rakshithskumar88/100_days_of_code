import random

rock = """
    _______
---'   ____)
      (_____)
      (_____)
      (____)
---.__(___)
"""

paper = """
    _______
---'   ____)____
          ______)
          _______)
         _______)
---.__________)
"""

scissors = """
    _______
---'   ____)____
          ______)
       __________)
      (____)
---.__(___)
"""

objects = [rock, paper, scissors]

your_choice = int(
    input("What do you choose? Type 0 for Rock, 1 for Paper or 2 for Scissors.\n")
)
if 0 <= your_choice <= 2:
    print(objects[your_choice])
print("Computer chose:")
computer_choice = random.randint(0, len(objects) - 1)
print(objects[computer_choice])

if your_choice < 0 or your_choice > 2:
    print("You typed an invalid input. You lose!")
elif your_choice == 0 and computer_choice == 2:
    print("You win!")
elif your_choice == 2 and computer_choice == 1:
    print("You win!")
elif your_choice == 1 and computer_choice == 0:
    print("You win!")
elif your_choice == computer_choice:
    print("Draw!")
else:
    print("You lose!")
