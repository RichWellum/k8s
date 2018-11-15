/*
 * p_g - Password Generator (until better name can be found)
 *
 * Create a password using a hash from a pass phrase so that the
 * same password will be generated for the same phrase. The user can
 * then use the tool to regenerate the password by simply remembering
 * the pass phrase.
 *
 * The hash is combined with a lexilogical letter from each word in
 * the pass phrase. Every other letter is capitalized.
 *
 * This is not crytologically safe by any means. The security of the
 * generated password is soley down to the pass phrase being used. If
 * the user uses 'password' as a passphrase, while still slightly more
 * secure than actually using 'password' as a password - it's not very
 * secure especially if this program gets hacked.
 *
 * Richard Wellum - March 2013
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAXTOKENS       256
#define MAXLINE         1024     /* fgets buff */
#define MINLEN          3        /* skip lines shorter as */

char **split(char *string, char *delim);
unsigned long ElfHash(const unsigned char *name);
char *strshuf(char *str);
char *str_add(int i);

int main(void) {
    char *delim = ".,:;`'\"+-_(){}[]<>*&^%$#@!?~/|\\= \t\r\n1234567890";
    char **tokens = NULL;
    char line[MAXLINE];
    int i = 0, y = 0, lcount = 0;
    unsigned long h = 0;

    puts("\nPassword generator. Generates a password from a pass phrase.");
    puts("The same passphrase generates the same password.");
    puts("The longer the passphrase the longer the generated password.");
    puts("\nEnter a password phrase, something easy to remember like: 'I like bananas'");

    while (fgets(line, MAXLINE, stdin) != NULL) {
	lcount++;

	if (strlen(line) < MINLEN) {
	    continue;
	}
	printf("\n== Line: %d, String: %s", lcount, line);

	h = ElfHash(line);
//	printf("\nElfHash is ***%d***\n", h);

	tokens = split(line, delim);
	printf("Password: ");

	/*
	 * Print out the first character of each token (word) of the
	 * passphrase.
	 */
	for (i = 0, y = 0; tokens[i] != NULL; i++, y++) {
//	    printf("%02d: %s\n", i, tokens[i]);

	    /* Capitalize every other character for some randomness */
	    if (!isOdd(i)) {
		tokens[i][y] = toupper(tokens[i][y]);
	    }
	    
	    /* Reset y if we have ran out of characters */
//	    printf("\n%s", tokens[i]);
	    if (!tokens[i][y]) {
		y = 0;
	    }
	    printf("%c", tokens[i][y]);
	}
	/* Add the hash and a useful character to separate */
	printf("%s%d\n", str_add(i), h);

	/* Free things up so we don't leak etc */
	for (i = 0; tokens[i] != NULL; i++) {
	    free(tokens[i]);
	}
	free(tokens);
    }
    return 0;
}

int isOdd (int i) {
    return (i % 2);
}

/*
 * The hash algorithm used in the UNIX ELF format for object files.
 * The input is a pointer to a string to be hashed .
 */

#define HASHSIZE 99777

unsigned long ElfHash (const unsigned char *name)
{
    unsigned long h = 0, g;
    static int M = HASHSIZE;

    while (*name)
    {
	h = (h << 4) + *name++;
	if (g = h & 0xF0000000L)
	    h ^= g >> 24;

	h &= ~g;
    }
    return h % M;
}

char *str_add (int i)
{
    /* Add more characters in between strings and hash */
    if (i == 1) {
	return ("!");
    } else if (i == 2) {
	return ("@");
    } else if (i == 3) {
	return ("#");
    } else if (i == 4) {
	return ("$");
    } else if (i == 5) {
	return ("%");
    } else if (i == 6) {
	return ("^");
    } else if (i == 7) {
	return ("&");
    } else if (i == 8) {
	return ("*");
    } else if (i == 9) {
	return (",");
    } else {
	return (":");
    }
}

/*
 * Useless function to shuffle a string deterministically that doesn't
 * work currently. Plus it leaks.
 */
char *strshuf (char *str) {
    int pick = 0;
    int len = 0;
    int i = 0;
    char tmp;
    char *retval = NULL;

    /* strip trailing newline */
    if (str[strlen(str) - 1] == '\n')
	str[strlen(str) - 1] = '\0';

    len = strlen(str) - 1;

    for (i = 0; i < len; i++) {
	pick = i++;
	/* swap orig char with pick */
	tmp = str[i];
	str[i] = str[i++];
	str[pick] = tmp;
    }

    retval = calloc(strlen(str) + 1, sizeof(char));
    strcpy(retval, str);

    return retval;
    free(retval);
}

/* split string into tokens, return token array */
char **split (char *string, char *delim) {
    char **tokens = NULL;
    char *working = NULL;
    char *token = NULL;
    int idx = 0;
    
    tokens  = malloc(sizeof(char *) * MAXTOKENS);
    if (tokens == NULL) {
	return NULL;
    }
    working = malloc(sizeof(char) * strlen(string) + 1);
    if (working == NULL) {
	return NULL;
    }
    /* to make sure, copy string to a safe place */
    strcpy(working, string);
    for (idx = 0; idx < MAXTOKENS; idx++) {
	tokens[idx] = NULL;
    }
    token = strtok(working, delim);
    idx = 0;
    
    /* always keep the last entry NULL terminated */
    while ((idx < (MAXTOKENS - 1)) && (token != NULL)) {
	tokens[idx] = malloc(sizeof(char) * strlen(token) + 1);
	if (tokens[idx] != NULL) {
	    strcpy(tokens[idx], token);
	    idx++;
	    token = strtok(NULL, delim);
	}
    }
    
    free(working);
    return tokens;
}
