##################################################################################
#Wczytanie potrzebnych bibliotek
import snap7
import matplotlib.pyplot as plt
import pandas as pd
import schedule
import time
import numpy


##################################################################################
#Utworzenie klienta 
plc = snap7.client.Client()
    #Połączenie z sterownikiem PLC za pomocą adresu IP (Slot i Rack)
plc.connect('169.254.90.50', 0, 1)


#Główna funkcja main przetwarzajaca dane
def main():
    stabilizacja = 0
    delta = 0.5
    stara = None 
    uchyb_wartosci = []
    

    while True:
        # Sprawdzenie zmiany danych
        setpoint, nowe_Wy, error, dt= Get_Real()
        uchyb_wartosci.append(error)
        Wyjscie_zapis_srawdz()
        
        if stara is None or setpoint != stara:  # Sprawdzenie, czy wartość setpoint zmieniła się
            stara = setpoint  # Zaktualizowanie zmiennej stara
            srednia, maks, min = fun1() # Wywołanie fun1 tylko raz po zmianie setpoint
        if setpoint == stara:
            if setpoint - delta <= nowe_Wy <= setpoint + delta:
                stabilizacja += 1
                if stabilizacja >= 10:
                    print("tab: ", uchyb_wartosci)
                    Zapis_txt(srednia, maks, min, Wsp_ISE(uchyb_wartosci), dt)
                    Wyjscie_odczyt()
                    stabilizacja = 0
            else:
                stabilizacja = 0

        time.sleep(1)  # Opóźnienie przed następną iteracją

    
###################################################################################
#Funkcje do wczytywania danych i ich analizy

#Odczyt zmienncyh z DB-ków z sterownika PLC
def PLC_COM():
    #Dane dotyczące zmiennych, które chcemy otrzymać
    DB_number_1 = 1
    Offset_number_1 = 0
    Length_1 = 4

    # Zwrot wartosci wyjscia
    DB_number_2 = 1
    Offset_number_2 = 4
    Length_2 = 4

    # Zwrot wartosci uchybu
    DB_number_3 = 3
    Offset_number_3 = 0
    Length_3 = 4

    # Zwrot wartości czasu (co do tego to jeszcze spytac i zrobic program PLC)
    DB_number_4 = 3
    Offset_number_4 = 4
    Length_4 = 4

    dane = plc.db_read(DB_number_1,Offset_number_1,Length_1) 
    wyjscie = plc.db_read(DB_number_2,Offset_number_2,Length_2)
    uchyb = plc.db_read(DB_number_3,Offset_number_3,Length_3)
    czas = plc.db_read(DB_number_4,Offset_number_4,Length_4)

    return dane, wyjscie, uchyb, czas
 
#Wyciągnięcie zmienncyh z DB-ków z sterownika PLC
def Get_Real():
    #numer DB, Offset numer, dlugosc danych w bajtach
    data_1, data_2, data_3, data_4 = PLC_COM()
    Zmienna_1 = snap7.util.get_real(data_1, 0)
    Zmienna_2 = snap7.util.get_real(data_2, 0)
    Zmienna_3 = snap7.util.get_real(data_3, 0)
    Zmienna_4 = snap7.util.get_real(data_4, 0)

    return Zmienna_1, Zmienna_2, Zmienna_3, Zmienna_4


#Funkcja obliczająca średnią
def średnia_wynik(size, y):  
    num = 0
    dod = 0
    war_sr = 0
    while num < size:
        for i in y:
            dod=dod+i
            num+=1
            war_sr = dod/size
    print("Wartość średnia: ", war_sr)
    return war_sr


#Funkcja wyliczająca współczynnik ISE, przyjmuje wartosci uchybu oraz czas, w jakim te wartosci wystepowaly
#Całka z kwadratu uchybu po czasie
def Wsp_ISE(errors):
    ISE = 0
    for error in errors:
        ISE += (error ** 2)  # Dodanie do sumy kwadratu błędu pomnożonego przez krok czasowy
    print("Warość współcznnnika ISE: ", ISE)
    return ISE


def fun1():
    Setpoint, _, _, _ = Get_Real()

    # Dane do zapisania do pliku Excel
    data = {
        'Y': [Setpoint],
    }

    #Próba odczytu istniejących danych z excela
    try:
        df_existing = pd.read_excel("liczby.xlsx") 
    except FileNotFoundError:
        df_existing = pd.DataFrame()
        
    #Stworzenie nowej ramki danych
    df_new = pd.DataFrame(data)

    #Tworzenie wartości X odpowiadających kolejnym liczbom naturalnym
    start_index = len(df_existing) + 1  #Indeks startowy dla X
    end_index = start_index + len(df_new)  #Indeks końcowy dla X
    x_values = list(range(start_index, end_index))

    #Dodanie kolumny X do ramki danych
    df_new['X'] = x_values

    #Połączenie nowych i starych danych tak, aby sie nie nadpisywały
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined.to_excel("liczby.xlsx", index=False)

    #Odczyt z excela
    df = pd.read_excel(r"C:\Users\kamil.mika\Desktop\DataAnalysisPLC\liczby.xlsx")

    #Przykładowe dane
    kolumna_x = 'X'
    kolumna_y = 'Y'

    ####### Dla danych z excela
    x = df[kolumna_x]
    y = df[kolumna_y]

    ########Wartości surowe
    #######x = [1, 2, 3, 4, 5]
    #######y = [1.5, 10, 6, 12, 10]
    size = len(y)

    #Znalezenie wartości maks i min (Dla wartości z excela)
    indeks_max = y.idxmax()
    indeks_min = y.idxmin()
    ########Dla wartości wpisanych
    #######indeks_max = y.index(max(y))
    #######indeks_min = y.index(min(y))
    maksymalny_punkt = (x[indeks_max], y[indeks_max])
    minimalny_punkt = (x[indeks_min], y[indeks_min])
    print("Wartość maksymalna: ", y[indeks_max])
    print("Wartość minimalna: ", y[indeks_min])

    #Wartość średnia
    wynik_srednia = str(średnia_wynik(size, y))
    
    #Wyswietlanie wartosci na wykresie (punkty)
    plt.figure()
    plt.scatter(x, y)
    plt.scatter(*maksymalny_punkt,color='red', label='Punkt maksymalny')
    plt.scatter(*minimalny_punkt,color='violet', label='Punkt minimalny')
    plt.title('Zbiór wyników')
    plt.xlabel('Oś X')
    plt.ylabel('Oś Y')
    plt.legend()
    plt.show()
    
    return wynik_srednia, str(y[indeks_max]), str(y[indeks_min])


def Wyjscie_zapis_srawdz():
    _, wyjscie, _, _ = Get_Real()

     # Dane do zapisania do pliku Excel
    data_output = {
        'Y': [wyjscie],
    } 

    #Próba odczytu istniejących danych z excela
    try:
        df_existing = pd.read_excel("Wyjscie.xlsx") 
    except FileNotFoundError:
        df_existing = pd.DataFrame()

    #Stworzenie nowej ramki danych
    df_new = pd.DataFrame(data_output)

    #Tworzenie wartości X odpowiadających kolejnym liczbom naturalnym
    start_index = len(df_existing) + 1  #Indeks startowy dla X
    end_index = start_index + len(df_new)  #Indeks końcowy dla X
    x_values = list(range(start_index, end_index))

    #Dodanie kolumny X do ramki danych
    df_new['X'] = x_values

    #Połączenie nowych i starych danych tak, aby sie nie nadpisywały
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined.to_excel("Wyjscie.xlsx", index=False)
    #time.sleep(0.001)


def Wyjscie_odczyt():
    #Odczyt z excela
    df = pd.read_excel(r"C:\Users\kamil.mika\Desktop\DataAnalysisPLC\Wyjscie.xlsx")

    #Przykładowe dane
    kolumna_x = 'X'
    kolumna_y = 'Y'

    ####### Dla danych z excela
    x = df[kolumna_x]
    y = df[kolumna_y]

    #Rysowanie wykresu
    plt.figure()
    plt.plot(x, y, 'red', linewidth = 2)
    plt.title('Przebieg wartości wyjściowych')
    plt.xlabel('Oś X')
    plt.ylabel('Oś Y')
    plt.show()


def Zapis_txt(srednia, maks, min, ISE, dt): 
    #Zapis do pliku
    f = open("Wyniki.txt", "w")
    f.write("Wartość średnia: " + srednia +'\n')
    f.write("Wartość maksymalna: " + maks +'\n')
    f.write("Wartość minimalna: " + min +'\n')
    f.write("Wartość współczynnika ISE: " + str(ISE) +'\n')
    f.write("Czas regulacji: " + str(dt) + "s"+'\n')
    f.close()

main()


