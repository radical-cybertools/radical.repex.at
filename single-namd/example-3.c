#include <stdio.h>
#include<sys/utsname.h>
#include <stdlib.h>
#include <math.h>
#include <sys/time.h>
#include <time.h>

#define N 2187
#define REPS 800000

void fred(int*);
double second(void);


int main(void){

 time_t now;
 int i,a;
 double time1, time2;

 struct utsname uname_pointer;

 uname(&uname_pointer);

 printf("Nodename    - %s \n", uname_pointer.nodename);

 time(&now);
 printf("start: %s", ctime(&now));

a=7;


  time1=second();
  for (i=0;i<REPS;i++){
     fred(&a);
  }
  if (a < 0) printf("Help!\n");
  time2=second();

  time(&now);
  printf("stop: %s", ctime(&now));

return 0;
}

void fred(int* pa){

   int i,j;
   int a,b,c,d,e;

   a = *pa;
   i=0;
   e=4;
   c=23;

   for (j=0;j<=N;j++) {
     e = c - j - j;
     b = c - j + c - j + c - j;
     d = b + e;
     i += 2;
     d = i;
     a += d + d + d;

   }

   *pa = a;
}

double second()
{

    struct timeval tp;
    struct timezone tzp;
    int i;

    i = gettimeofday(&tp,&tzp);
    return ( (double) tp.tv_sec + (double) tp.tv_usec * 1.e-6 );
}

                                                                                                                                           

