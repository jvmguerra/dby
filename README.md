Resumo Trabalho
===============

#Arquivos

- Tamanho fixo de uma página = 4KB.
- A primeira página de um arquivo é sempre um *diretório*.
- Para referenciar uma página fora de um arquivo, basta utilizar um inteiro (unsigned), o qual dirá em qual posição a página se encontra:
    
        E.g.: int = 3 -> terceira página 
    
    Assim, o endereço exato da página será (int-1) * 4KB.

- Tamanho máximo de um arquivo é 4GB.

##Diretório

O diretório é uma, ou várias, página(s) especiais de um arquivo. Por meio dele podemos verificar a quantidade de espaço livre em cada uma das outras páginas do arquivo. 

Como pode haver mais páginas no arquivo do que há entradas no diretório, o diretório pode ser maior que 1 página. Para isso, existe um campo no diretório que é o ponteiro para a próxima página do diretório.

####Inserção de um novo registro 

Varrer o diretório procurando pela primeira entrada com espaço livre suficiente para acomodar o registro. Caso não encontre, usar o ponteiro para a próxima página de diretório e continuar a busca.

####Campos

- base = 4 bytes(unsigned)
    
    é o endereço base de onde a página (do diretório) começa. Usado para saber o endereço correto -- base * index -- de cada entrada contida no diretório. 

- numOfEntries = 2 bytes(unsigned)
    
    é a quantidade de entradas no diretório.

- nextDir = 4 bytes(unsigned)
    
    é o ponteiro para a próxima página do diretório.

- counters = 2 bytes(unsigned)
    
    são *numOfEntries*-campos no diretório que armazenam a quantidade de espaço livre em cada *numOfEntries*-página. A posição (index) do counter na página, indica qual página ele referencia por meio do cálculo: index * base.


##Páginas para Armazenamento de Registros

São coleções de registros; no caso, registros de tamanho variável. Cada registro possui um campo especial na página chamado de *slot*, além do espaço ocupado pelo próprio registro. Esses *slots* permitem localizar um registro facilmente, e possibilitam que um registro realocado continue sendo identificado pelo mesmo id (índice do slot).

####Crescimento de um Registro

O seu slot irá apontar para um novo espaço alocado. Esse espaço alocado pode ser: 

1. um espaço livre; haverá a criação de um novo slot com um tamanho negativo, referenciando o espaço anteriormente ocupado pelo registro.

2. um espaço que não estava mais sendo utilizado por um outro slot. 

3. em uma outra página, devido à falta de espaço nessa mesma página; seu regStart terá o endereço base da nova página, e o regSize terá o id do novo slot. 

####Inserção de um novo registro

1. Caso haja espaço livre suficiente para armazenar o registro: criar um novo slot e armazenar o registro.

2. Caso haja um slot desocupado com espaço suficiente, utilizar tal slot.

3. Procurar outra página para inserir o registro.

####Campos

- freeSpace = 2 bytes(unsigned)
    
    Endereço do começo do espaço livre. Em geral, o espaço livre estende-se até o final da páginha (base + 4KB - (fieldsSize)).

- numOfEntries = 2 byte (unsigned)
    
    Quantidade de registros armazenados na página, e consequentemente, é também a quantidade de slots da página. 

- registerSlots = 6 bytes **:**
    + regStart = 4 bytes (unsigned)

        Endereço do começo do i-registro. esse endereço pode até ser em outra página, caso o registro tenha crescido e não teve espaço para permanecer na mesma página; o regSize, nesse caso, terá o id do slot desse registro nessa outra página.

    + regSize = 2 bytes (signed)

        Espaço ocupado pelo i-registro. Caso for negativo, o espaço não está mais sendo ocupado pelo registro.


##Registros

Os registros podem armazenar dois tipo de variáveis: inteiro e varchar. Os inteiros tem um tamanho fixo de 4 bytes. Os varchar, usados para armazenar "frases", podem ser declarados em até 3KB. No entanto, a partir do momento que são declarados pelo usuário, eles só podem crescer até o limite dado.

Como o varchar é de tamanho variável, o tamanho total de um registro também é variável. O espaço usado pelo varchar é o tamanho da frase e mais 20% de espaço livre. Caso o valor armazenado cresça e não caiba no espaço, é necessário realocar o registro.

####Campos

- int = 4 bytes (signed)

- sizeOfChar = 2 bytes (unsigned), 0 >= sizeOfChar <= 3KB

    É o tamanho real que a variável varchar ocupa. Caso seja 0, não há valor armazenado no varchar.

- varchar = sizeOfChar * 1.2 bytes

    Ocupa o espaço do valor (frase) em questão, e deixa um espaço extra livre de 20%. O espaço extra serve para otimizar o crescimento da frase, tentando evitar o realocamento de todo o registro. No entanto, tal espaço nunca excede o limite declarado pelo usuário da varchar.

    







Ele pode ter apenas 1 byte (0 a 255) porque *(4KB - 256 \* (registerEntries = 4)) / 256 <= 12* . Assim, o tamanho médio dos registros é de no máximo 12 bytes, o que