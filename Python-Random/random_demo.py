import random

#random a number between 0 to 1
value = random.random()
print (value)

#random a number between certain range like 1-100
#but not a beautiful one same as 6.121848
value1 = random.uniform(1,100)
print (value1)

#random a number between certain range like 1-100
#this method include number 1 and 100 in the random numbers
value2 = random.randint(1,100)
print (value2)

#random a word from a list like the first item that say hey
greetings = ['hey', 'Hello','hi','howdy','What\'s up?']
value3 = random.choice(greetings)
Name = ', Name!' #Enter Your name
print (value3 + Name)

#random a roulette of a word from a list that in the example includes color
#the K value is how much time to "spin the roulette"
colors = ['Red', 'Black','Green','Pink','White','Blue']
value4 = random.choices(colors, k = 10)
print (value4)

#random a roulette of a word from a list that in the example includes color
#the weights value is how much Chance we want to give to every item on the list
#how much rare the item is
colors = ['Red', 'Black','Green','Pink','White','Blue']
value5 = random.choices(colors, weights=[18,2,16,2,10,4] ,k = 10)
print (value5)

#random a like list of card from 1 to 52 the 53 its not included
deck = list(range(1, 53))
random.shuffle(deck) #this command is like shuffles(mixes) the cards
print (deck)

#this command is shuffles the cards and don`t print out the same card
deck = list(range(1, 53))
unique_card = random.sample(deck, k=5) #here
print (unique_card)
