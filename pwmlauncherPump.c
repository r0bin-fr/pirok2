#include <wiringPi.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

//16 et 100 = 12Khz
//128 et 100 = 1,5Khz
//32 et 100 = 6Khz
//18=PWM matériel RPi
#define PWCLKDIVIDER	256//128 //16 //2
#define PWRANGE  	100 //4000
#define GPIOPINPWM	18 //13

/*****************************************
 * WiringPi launcher to set PWM          *
 * based on James Ward PWM settings      *
 * to work with SSR and Espresso machine *
 *****************************************/
int main (int argc, char *argv[])
{
  int drive = 0;
  int doinit = 0;

  if(argc != 3)
  {
	printf("Error: invalid arguments. Usage: sudo pwmlauncherPump <a> <bbb> where a is init (1 or 0) and bbb is the drive percent\n");
	exit(0); 
  }
  //printf ("Welcome into PWM drive launcher\n") ;
  //retrieve init argument
//  doinit = atoi(argv[1]);

  //retrieve drive argument
  drive = atoi(argv[2]);
  if(drive > 100)
    drive = 100;
//  printf("pump drive=%d%\n",drive);

  //init wiringpi
	if (wiringPiSetupGpio() == -1){
    		printf("Error inint wiringpi lib\n");
    		exit (1) ;
  	}
    
//  if(doinit){
//	printf("init pwm pump\n");

  	//PWM mode
  	pinMode(GPIOPINPWM,PWM_OUTPUT);
  	//PWM "predictive mode"
  	pwmSetMode(PWM_MODE_MS); 

  	//set clock at 2Hz (clock divider / range)
  	pwmSetClock(PWCLKDIVIDER);
  	pwmSetRange (PWRANGE) ;
  //}

  //setting drive according to the RANGE 
  pwmWrite (GPIOPINPWM, (drive * (PWRANGE / 100))); 
}
