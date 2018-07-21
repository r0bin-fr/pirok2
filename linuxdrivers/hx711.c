/*
  * Experimental Kernel module for Hx711 scale
  *
  * Author: M.Hameau - 80% based on Andreas Klinger work on HX711 IIO linux driver
  * Released under the GPL
  *
  */

#include <linux/kobject.h>
#include <linux/string.h>
#include <linux/sysfs.h>
#include <linux/module.h>
#include <linux/init.h>
#include <linux/gpio.h>
#include <linux/interrupt.h>
#include <linux/time.h>
#include <linux/ktime.h>
#include <linux/delay.h>
#include <linux/sched.h>
#include <linux/irq.h>

/*---------------------------------------------------------------------------*/

/* The Kernel object */
static struct kobject *s_kernelObject = NULL;

/* GPIO pin used for trigger out */
static int g_sck = 20;
module_param(g_sck, int, S_IRUGO);

/* GPIO pin used for g_dt in */
static int g_dt = 19;
module_param(g_dt, int, S_IRUGO);

/* Mutex used to prevent simultaneous access */
static DEFINE_MUTEX(mutex);

int			g_gain_set;	/* gain set on device */
int			g_gain_chan_a;	/* gain for channel A */
/*
	 * triggered buffer
	 * 2x32-bit channel + 64-bit timestamp
	 */
u32			g_buffer[4];
	
/*---------------------------------------------------------------------------*/

/* gain to pulse and scale conversion */
#define HX711_GAIN_MAX		3

struct hx711_gain_to_scale {
	int			gain;
	int			gain_pulse;
	int			scale;
	int			channel;
};

/*
 * .scale depends on AVDD which in turn is known as soon as the regulator
 * is available
 * therefore we set .scale in hx711_probe()
 *
 * channel A in documentation is channel 0 in source code
 * channel B in documentation is channel 1 in source code
 */
static struct hx711_gain_to_scale hx711_gain_to_scale[HX711_GAIN_MAX] = {
	{ 128, 1, 0, 0 },
	{  32, 2, 0, 1 },
	{  64, 3, 0, 0 }
};

static int hx711_get_gain_to_pulse(int gain)
{
	int i;

	for (i = 0; i < HX711_GAIN_MAX; i++)
		if (hx711_gain_to_scale[i].gain == gain)
			return hx711_gain_to_scale[i].gain_pulse;
	return 1;
}

static int hx711_get_gain_to_scale(int gain)
{
	int i;

	for (i = 0; i < HX711_GAIN_MAX; i++)
		if (hx711_gain_to_scale[i].gain == gain)
			return hx711_gain_to_scale[i].scale;
	return 0;
}

static int hx711_get_scale_to_gain(int scale)
{
	int i;

	for (i = 0; i < HX711_GAIN_MAX; i++)
		if (hx711_gain_to_scale[i].scale == scale)
			return hx711_gain_to_scale[i].gain;
	return -EINVAL;
}

static int hx711_cycle( void )
{
	int val;

	/*
	 * if preempted for more then 60us while PD_SCK is high:
	 * hx711 is going in reset
	 * ==> measuring is false
	 */
	preempt_disable();
//	gpiod_set_value(hx711_data->gpiod_pd_sck, 1);
//	val = gpiod_get_value(hx711_data->gpiod_dout);
	gpio_set_value(g_sck, 1);
	val = gpio_get_value(g_dt);
	/*
	 * here we are not waiting for 0.2 us as suggested by the datasheet,
	 * because the oscilloscope showed in a test scenario
	 * at least 1.15 us for PD_SCK high (T3 in datasheet)
	 * and 0.56 us for PD_SCK low on TI Sitara with 800 MHz
	 */
//	gpiod_set_value(hx711_data->gpiod_pd_sck, 0);
	gpio_set_value(g_sck, 0);

	preempt_enable();

	return val;
}

static int hx711_read( void )
{
	int i, ret;
	int value = 0;
//	int val = gpiod_get_value(hx711_data->gpiod_dout);
	int val = gpio_get_value(g_dt);

	/* we double check if it's really down */
	if (val)
		return -EIO;

	for (i = 0; i < 24; i++) {
		value <<= 1;
		ret = hx711_cycle();
		if (ret)
			value++;
	}

	value ^= 0x800000;

	for (i = 0; i < hx711_get_gain_to_pulse(g_gain_set); i++)
		hx711_cycle();

	return value;
}

static int hx711_wait_for_ready( void )
{
	int i, val;

	/*
	 * in some rare cases the reset takes quite a long time
	 * especially when the channel is changed.
	 * Allow up to one second for it
	 */
	for (i = 0; i < 100; i++) {
//		val = gpiod_get_value(hx711_data->gpiod_dout);
		val = gpio_get_value(g_dt);
		if (!val)
			break;
		/* sleep at least 10 ms */
		msleep(10);
	}
	if (val)
		return -EIO;

	return 0;
}

static int hx711_reset( void )
{
	int ret;
//	int val = gpiod_get_value(hx711_data->gpiod_dout);
	int val = gpio_get_value(g_dt);

	if (val) {
		/*
		 * an examination with the oszilloscope indicated
		 * that the first value read after the reset is not stable
		 * if we reset too short;
		 * the shorter the reset cycle
		 * the less reliable the first value after reset is;
		 * there were no problems encountered with a value
		 * of 10 ms or higher
		 */
//		gpiod_set_value(hx711_data->gpiod_pd_sck, 1);
//		msleep(10);
//		gpiod_set_value(hx711_data->gpiod_pd_sck, 0);
		gpio_set_value(g_sck, 1);
		msleep(10);
		gpio_set_value(g_sck, 1);

		ret = hx711_wait_for_ready();
		if (ret)
			return ret;
		/*
		 * after a reset the gain is 128 so we do a dummy read
		 * to set the gain for the next read
		 */
		ret = hx711_read();
		if (ret < 0)
			return ret;

		/*
		 * after a dummy read we need to wait vor readiness
		 * for not mixing gain pulses with the clock
		 */
		val = hx711_wait_for_ready();
	}

	return val;
}

static int hx711_set_gain_for_channel(int chan)
{
	int ret;

	if (chan == 0) {
		if (g_gain_set == 32) {
			g_gain_set = g_gain_chan_a;

			ret = hx711_read();
			if (ret < 0)
				return ret;

			ret = hx711_wait_for_ready();
			if (ret)
				return ret;
		}
	} else {
		if (g_gain_set != 32) {
			g_gain_set = 32;

			ret = hx711_read();
			if (ret < 0)
				return ret;

			ret = hx711_wait_for_ready();
			if (ret)
				return ret;
		}
	}

	return 0;
}

static int hx711_reset_read(int chan)
{
	int ret;
	int val;

	/*
	 * hx711_reset() must be called from here
	 * because it could be calling hx711_read() by itself
	 */
	if (hx711_reset()) {
		printk("reset failed!\n");
		return -EIO;
	}

	ret = hx711_set_gain_for_channel(chan);
	if (ret < 0)
		return ret;

	val = hx711_read();

	return val;
}


//    irq = gpio_to_irq( g_dt );
//	gpio_set_value(g_sck, 0);

/*---------------------------------------------------------------------------*/
#define MATT_NB_SCALES 5
#define MATT_RETRY 3
/* This function is called when the 'scale' kernel object is read */
static ssize_t scale_show(
    struct kobject *object,
    struct kobj_attribute *attribute,
	char *buffer
) {
/*	int val = hx711_read();

	if(val == -EIO)
		return sprintf( buffer, "error\n");
	else
		return sprintf( buffer, "%d\n", val );
*/
	int i, j,val;
	int nbvals = 0;
	int totalv = 0;
	//multiple reads to get more accuracy
	for(i=0;i<MATT_NB_SCALES;i++){
		val = hx711_read();
		j=0;
		//loop on error
		while((val == -EIO) && (j<MATT_RETRY)){
			val = hx711_read();
			j++;
			msleep(10);
		}
		if(val != -EIO){
			totalv += val;
			nbvals ++;
			msleep(10);
		}
	}
	//compute average
	totalv = totalv / nbvals;
//	return sprintf( buffer, "%d/%d\n", totalv, nbvals );
	return sprintf( buffer, "%d\n", totalv );
}

/*---------------------------------------------------------------------------*/

/* Attribute representing the 'scale' kernel object, which is read only */
static struct kobj_attribute scaleAttribute = __ATTR_RO(scale);

/*---------------------------------------------------------------------------*/

/* List of all attributes */
static struct attribute *attrs[] = {
	&scaleAttribute.attr,
	NULL    /* terminate the list */
};

/*---------------------------------------------------------------------------*/

/* Attribute group */
static struct attribute_group attributeGroup = {
	.attrs = attrs
};

/*---------------------------------------------------------------------------*/

/* Initialise GPIO */
static int gpioInit( void )
{
    /* check that trigger GPIO is valid */
    if ( !gpio_is_valid(g_sck) ){
        printk( KERN_ALERT "g_sck GPIO %d is not valid\n", g_sck );
        return -EINVAL;
    }

    /* request the GPIO pin */
    if( gpio_request(g_sck, "hx711") != 0 ) {
        printk( KERN_ALERT "Unable to request g_sck GPIO %d\n", g_sck );
        return -EINVAL;
    }

    /* make GPIO an output */
    if( gpio_direction_output(g_sck, 0) != 0 ) {
        printk( KERN_ALERT "Failed to make g_sck GPIO %d an output\n", g_sck );
        return -EINVAL;
    }

    /* check that g_dt GPIO is valid */
    if ( !gpio_is_valid(g_dt) ){
        printk( KERN_ALERT "g_dt GPIO %d is not valid\n", g_dt );
        return -EINVAL;
    }

    /* request the GPIO pin */
    if( gpio_request(g_dt, "hx711") != 0 ) {
        printk( KERN_ALERT "Unable to request g_dt GPIO %d\n", g_dt );
        return -EINVAL;
    }

    /* make GPIO an input */
    if( gpio_direction_input(g_dt) != 0 ) {
        printk( KERN_ALERT "Failed to make g_dt GPIO %d an input\n", g_dt );
        return -EINVAL;
    }

	g_gain_set = 128;
	g_gain_chan_a = 128;
	/* now reset on channel A */
	hx711_reset_read(0);
	
    return 0;
}

/*---------------------------------------------------------------------------*/

/* Free GPIO */
static void gpioFree( void )
{
    gpio_free(g_sck);
    gpio_free(g_dt);
}

/*---------------------------------------------------------------------------*/

/* Module initialisation function */
static int __init moduleInit( void )
{
	int result = -1;

	/* Create /sys/kernel/hx711 representing the sensor */
	s_kernelObject = kobject_create_and_add( "hx711", kernel_kobj );
	if ( s_kernelObject == NULL )
		return -ENOMEM;

	/* Create the files associated with this kobject */
	result = sysfs_create_group( s_kernelObject, &attributeGroup );
	if ( result ) {
	    /* Failed: clean up */
		kobject_put( s_kernelObject );
		return result;
	}

	/* Set up the GPIO */
	if ( gpioInit() < 0 )
	    return -EINVAL;

	return result;
}

/*---------------------------------------------------------------------------*/

/* Module exit function */
static void __exit moduleExit( void )
{
    /* Decrement refcount and clean up if zero */
    kobject_put( s_kernelObject );

    /* Free GPIO */
    gpioFree();
}

/*---------------------------------------------------------------------------*/

module_init(moduleInit);
module_exit(moduleExit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("M. Hameau");

/*---------------------------------------------------------------------------*/


