from send_game_data import main
from read_game_data import main_r
import time

# Durée maximale pour essayer la fréquence (en secondes)
MAX_TRY_TIME = 5  

t = 0
while t == 0:
    target = main()
    start_time = time.time()
    success = False

    # On laisse l'utilisateur essayer pendant MAX_TRY_TIME secondes
    while time.time() - start_time < MAX_TRY_TIME:
        freq_util = main_r()
        print(f"Votre fréquence: {freq_util} Hz")  # optionnel pour feedback

        if target - 40 <= freq_util <= target + 40:
            print("Bravo !")
            success = True
            break  # quitte la boucle interne si réussi
        time.sleep(0.1)  # petit délai pour ne pas saturer le CPU

    if not success:
        print("Perdu !")
        t = 1  # met fin à la boucle principale
