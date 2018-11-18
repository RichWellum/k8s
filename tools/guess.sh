#!/bin/bash
# #!/usr/bin/bash

function press_enter
{
    echo ""
    echo -n "Press Enter to play again (CTRL-C to quit) "
    read
    clear
}

function gen_num
{
    echo
    echo -n "Select a max number: "
    echo
    echo "1 - 100"
    echo "2 - 500"
    echo "3 - 1000"
    echo "4 - 5000"
    echo "5 - 25000"
    echo ""
    echo "0 - exit program"
    echo ""
    read selection
    case $selection in
        1 ) max=100 ;;
        2 ) max=500 ;;
        3 ) max=1000 ;;
        4 ) max=5000 ;;
        5 ) max=25000 ;;
        0 ) exit ;;
        * ) continue ;;
    esac

    echo ""

    min=0
    goes=0
    solution=$RANDOM
    let "solution %= $max"
}

gen_num

while true
do
    goes=$((goes+1))

    echo -n "Guess a number between $min-$max($goes): "
    read guess
    echo ""

    if [ "`echo $guess | egrep ^[[:digit:]]+$`" = "" ]; then
        echo " '$guess' is not a number"
        echo
        continue
    fi

    if [ "$guess" -eq "$solution" ]; then
        echo "Well done the answer was '$solution' and it took you '$goes' guesses."
        press_enter
        gen_num
        continue
    fi

    if [ "$guess" -lt "$min" -o "$guess" -ge "$max" ]; then
        continue;
    fi

    if [ "$guess" -lt "$solution" ]; then
        min=$guess
    else
        max=$guess
    fi
done
