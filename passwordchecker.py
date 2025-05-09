#Password Checker from my previous Object Oriented Programming assessment

import sqlite3
import math


class PasswordChecker:
    def __init__(self):
        self._password = ""

        #Total score
        self._score = 0

        #List of possible scores for password
        self.RATINGS = ["Very Weak","Weak","Moderately Strong","Very Strong"]

        #The current password rating
        self._current_rating = ""

        #Individual scores for character types
        self._length_score = 0
        self._character_score = 0
        self._rarity_score = 0

        #Counter for types of charcters
        self._specialCount = []
        self._numberCount = []
        self._upperCount = []
        self._lowerCount = []

        #Initialise connection to database at intit to decrease processing time later
        self._passwordsConnection = sqlite3.connect("common_passwords.db")
        self._cursor = self._passwordsConnection.cursor()
        

        
        
    

    #Methods - 'score' functions return an integer between 0-100
    def score_length(self): #Scores based on password length

        #Scores based on length using an exponential function
        self._length_score = min(math.ceil((2**len(self._password))/80)+5*len(self._password),100)

    def score_characters(self): #Scores based on special characters/number used
        self._numberCount = []
        self._upperCount = []
        self._lowerCount = []
        self._specialCount = []
        
        #Does not count duplicates of same character
        for char in self._password:
            if char.isnumeric() and char not in self._numberCount:
                self._numberCount.append(char)
            elif char.isupper() and char not in self._upperCount:
                self._upperCount.append(char)
            elif char.islower() and char not in self._lowerCount:
                self._lowerCount.append(char)
            elif not char.isalnum() and char not in self._specialCount:#If it is neither a number or letter, it is a special character
                self._specialCount.append(char)
        
        #Max score achieved by 2 of each type (numbers, uppercase, lowercase, special characters)
        #Second character of each type is worth less
        #Lowercase scores less
        self._character_score = min(30, len(self._numberCount) * 17) + min(30, len(self._specialCount) * 17) + min(30, len(self._upperCount) * 17) + min(10, len(self._lowerCount) * 5)

    def score_rarity(self): #Scores on the commoness of the password
        #Access database and check for password
        self._cursor.execute(
            "SELECT ROWID, COUNT(1) FROM passwords WHERE value = ?",
            (self._password,)
        )

        #Store its row in the database (or None if not in database)
        passwordRow = self._cursor.fetchone()[0]

        #Check if the password was in a row
        if passwordRow != None:
            #Return a lower value the more common the password
            self._rarity_score = min(round(passwordRow/5),90)#Gives a score between 0 and 99
        else:
            #Not a common password
            self._rarity_score = 100

    
    def contains_password(self):
        if "password" in self._password.lower():
            return True
        else:
            return False

    #Combines all scores using weightings
    def combine_scores(self,lengthWeight,characterWeight,rarityWeight):
        if self.contains_password():
            self._score = 0
        else:
            totalWeight = lengthWeight + characterWeight + rarityWeight
            weightedLength = ((self._length_score/totalWeight)*lengthWeight)
            weightedCharacters = ((self._character_score/totalWeight)*characterWeight)
            weightedRarity = ((self._rarity_score/totalWeight)*rarityWeight)
        
            #The total score is the sum of the weighted scores

            self._score = int(weightedLength + weightedCharacters + weightedRarity)

            #Decrease overall score if any individual score is extremely low
            if self._length_score <= 20 or self._character_score <= 20 or self._rarity_score <= 20:
                self._score /= 2

    #Give a rating based on score
    def rate_password(self):
        #The size of each rating 'bracket'
        ratingSize = 100//len(self.RATINGS)

        #Repeats until the score is lower than the current rating bracket
        completed = False
        for ratingBracket in range(1,len(self.RATINGS)+1):
            if self._score <= ratingSize * ratingBracket and not completed:
                self._current_rating = self.RATINGS[ratingBracket-1]
                completed = True
            

    #Generates feedback based on score
    def generate_feedback(self, feedbackMode):
        feedback = ""

        if self.contains_password():
            feedback += "Don't put 'password' in your password. That's just lazy."
        elif self._score == 100:
            feedback += "Your password has achieved the maximum score. You have a very secure password!"
        else:
            feedback += f"Your password is {self._current_rating.lower()}."
            

            #Choose type of feedback
            if feedbackMode == "text":
                feedback += self.written_feedback()
                
            elif feedbackMode == "star":
                feedback += self.star_feedback()

        return feedback

    def written_feedback(self):
        #Generate text based on what can be improved
        
        feedback = ""

        #Stores score of each type of 'problem'
        problems = [self._length_score, self._character_score, self._rarity_score]
            
        
        #Check if any other issues are present

        #Length
        if problems[0] < 50:
            feedback += "\n\nYour password is very short. It could be strengthened greatly by making it longer."
        elif problems[0] < 100:
            feedback += "\n\nYour password is moderately long, but would be stronger if it was slightly longer."
        
        #Character variety
        if problems[1] < 100:

            if problems[1] < 50:
                feedback += "\n\nYou do not have a very large variety of characters in your password. "
            else:
                feedback += "\n\nYou could strengthen your password by adding a few more different characters. "

            #Get all types of characters and their corresponding names
            characterTypes = {"special character":len(self._specialCount),"number":len(self._numberCount),"uppercase letter":len(self._upperCount),"lowercase letter":len(self._lowerCount)}
            
            

            #Check each type of character

            unusedTypes = []#Stores types of character that are not used

            singleUseTypes = []#Stores types of character that are only used once

            for characterType in characterTypes:
                if characterTypes[characterType] <= 0:
                    unusedTypes.append(characterType)

                elif characterTypes[characterType] == 1:
                    singleUseTypes.append(characterType)
            
            if len(unusedTypes) > 0:

                if len(unusedTypes) > 1:
                    #Add grammar between characters
                    unusedString = "s, ".join(unusedTypes[:len(unusedTypes)-1:]) + "s or " + unusedTypes[len(unusedTypes)-1]
                else:
                    unusedString = unusedTypes[0]
                
                feedback += f"You have not used any {unusedString}s. "

            if len(singleUseTypes) > 0:

                if len(singleUseTypes) > 1:
                    #Add grammar between characters
                    singleUsedString = ", ".join(singleUseTypes[:len(singleUseTypes)-1:]) + " and " + singleUseTypes[len(singleUseTypes)-1]
                else:
                    singleUsedString = singleUseTypes[0]
                
                feedback += f"You have only used one type of {singleUsedString}. "
            
        #Rarity
        if problems[2] < 100:
            feedback += f"\n\nYour password is very commonly used. Try to create a more unique password."
            
        return feedback

    def star_feedback(self):
        #Generate star ratings based on each category
        feedback = ""

        allScores = {"Length":self._length_score, "Character Variety":self._character_score, "Creativity":self._rarity_score}

        for score in allScores:
            feedback += "\n\n"
            feedback += f"{score}: \n"

            #Add stars
            for i in range(5):
                if allScores[score] >= (i+1)*20:
                    feedback += "★"
                else:
                    feedback += "☆"
            
        
        return feedback


    #Getter methods
    def get_password(self):
        return self._password
    
    def get_score(self):
        return self._score
    
    def get_length_score(self):
        return self._length_score
    
    def get_character_score(self):
        return self._character_score
    
    def get_rarity_score(self):
        return self._rarity_score

    def get_rating(self):
        return self._current_rating

    #Setter methods
    def update_password(self,new_password):
        self._password = new_password
