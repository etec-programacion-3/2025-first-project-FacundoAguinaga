def pedir_numero(mensaje):
    while True:
        entrada = input(mensaje)
        try:
            return float(entrada)
        except ValueError:
            print("Por favor, ingresá un número válido.")

def restar(a, b):
    return a - b

# Pedimos los números al usuario
num1 = pedir_numero("Ingresá el primer número: ")
num2 = pedir_numero("Ingresá el segundo número: ")

# Calculamos la resta
resultado = restar(num1, num2)

print("El resultado de la resta es: ", resultado)
