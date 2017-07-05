import random

class EmbedFooter: #for picking a funny embed footer message
    def __init__(self):
        self.message = self.setRandom()
    def __repr__(self):
        return self.message
    def __str__(self):
        return self.message
    def setRandom(self):
        list = {"Produced with precision", "You ever just put butter on saltine crackers?", "Look at me now", "Filled with love", "Made with love", "Produced with no care", "Produced by the producer", "Produced carefully", "Created by hand", "Created by the hand of God", "Baked to perfection", "Created carefully", "Carelessly made", "Organically produced", "Molded by Picasso himself", "I'm not an artist", "Don't judge", "Dali would have been proud", "Look at my doge face", "how did this get here", "Over 3 man-seconds were spent creating this", "oh god i am not good with computer", "Carefully constructed by an artist", "This was easier than it sounds", "hi"}
        return random.sample(list, 1)[0]